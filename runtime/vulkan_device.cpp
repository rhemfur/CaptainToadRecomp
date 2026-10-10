// Headless Vulkan device bootstrap and a synthetic image-clear/readback test.
#include "runtime.h"
#include "platform/host.h"
#include "vulkan_device.h"
#define VK_NO_PROTOTYPES
#include <vulkan/vulkan.h>
#include <memory>
#include <mutex>

namespace {
struct Device {
    void* library=nullptr;
    PFN_vkGetInstanceProcAddr get=nullptr;
    PFN_vkGetDeviceProcAddr device_get=nullptr;
    VkInstance instance=VK_NULL_HANDLE;
    VkPhysicalDevice physical=VK_NULL_HANDLE;
    VkDevice device=VK_NULL_HANDLE;
    VkQueue queue=VK_NULL_HANDLE;
    uint32_t queue_family=0;
    VkPhysicalDeviceMemoryProperties memory{};
    template<class T> T instance_proc(const char* name) {
        auto result=reinterpret_cast<T>(get(instance,name));
        if (!result) fatal("[ct-vulkan] missing instance entry %s",name);
        return result;
    }
    template<class T> T proc(const char* name) {
        auto result=reinterpret_cast<T>(device_get(device,name));
        if (!result) fatal("[ct-vulkan] missing device entry %s",name);
        return result;
    }
    ~Device() {
        if (device) proc<PFN_vkDestroyDevice>("vkDestroyDevice")(device,nullptr);
        if (instance) instance_proc<PFN_vkDestroyInstance>("vkDestroyInstance")(instance,nullptr);
        if (library) {
#ifdef _WIN32
            FreeLibrary(static_cast<HMODULE>(library));
#else
            dlclose(library);
#endif
        }
    }
    bool initialize() {
#ifdef _WIN32
        library=LoadLibraryW(L"vulkan-1.dll");
        if (library) get=reinterpret_cast<PFN_vkGetInstanceProcAddr>(GetProcAddress(static_cast<HMODULE>(library),"vkGetInstanceProcAddr"));
#else
        library=dlopen("libvulkan.so",RTLD_NOW|RTLD_LOCAL);
        if (library) get=reinterpret_cast<PFN_vkGetInstanceProcAddr>(dlsym(library,"vkGetInstanceProcAddr"));
#endif
        if (!get) { LOG("[ct-vulkan] system loader unavailable"); return false; }
        auto create=reinterpret_cast<PFN_vkCreateInstance>(get(nullptr,"vkCreateInstance"));
        if (!create) return false;
        VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};
        app.pApplicationName="Captain Toad headless diagnostic"; app.apiVersion=VK_API_VERSION_1_3;
        VkInstanceCreateInfo info{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO}; info.pApplicationInfo=&app;
        auto result=create(&info,nullptr,&instance);
        if (result!=VK_SUCCESS) { LOG("[ct-vulkan] instance creation failed: %d",result); return false; }
        auto enumerate=instance_proc<PFN_vkEnumeratePhysicalDevices>("vkEnumeratePhysicalDevices");
        uint32_t count=0;
        if (enumerate(instance,&count,nullptr)!=VK_SUCCESS || !count) return false;
        std::vector<VkPhysicalDevice> devices(count);
        if (enumerate(instance,&count,devices.data())!=VK_SUCCESS) return false;
        auto properties=instance_proc<PFN_vkGetPhysicalDeviceProperties>("vkGetPhysicalDeviceProperties");
        auto families=instance_proc<PFN_vkGetPhysicalDeviceQueueFamilyProperties>("vkGetPhysicalDeviceQueueFamilyProperties");
        auto create_device=instance_proc<PFN_vkCreateDevice>("vkCreateDevice");
        device_get=instance_proc<PFN_vkGetDeviceProcAddr>("vkGetDeviceProcAddr");
        for (auto candidate:devices) {
            VkPhysicalDeviceProperties prop{}; properties(candidate,&prop);
            if (prop.apiVersion<VK_API_VERSION_1_3) continue;
            uint32_t family_count=0; families(candidate,&family_count,nullptr);
            std::vector<VkQueueFamilyProperties> queue_properties(family_count);
            families(candidate,&family_count,queue_properties.data());
            for (uint32_t family=0;family<family_count;++family) {
                if (!queue_properties[family].queueCount || !(queue_properties[family].queueFlags&VK_QUEUE_GRAPHICS_BIT)) continue;
                float priority=1;
                VkDeviceQueueCreateInfo queue_info{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
                queue_info.queueFamilyIndex=family; queue_info.queueCount=1; queue_info.pQueuePriorities=&priority;
                VkDeviceCreateInfo device_info{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};
                device_info.queueCreateInfoCount=1; device_info.pQueueCreateInfos=&queue_info;
                result=create_device(candidate,&device_info,nullptr,&device);
                if (result!=VK_SUCCESS) continue;
                physical=candidate; queue_family=family;
                proc<PFN_vkGetDeviceQueue>("vkGetDeviceQueue")(device,family,0,&queue);
                instance_proc<PFN_vkGetPhysicalDeviceMemoryProperties>("vkGetPhysicalDeviceMemoryProperties")(physical,&memory);
                LOG("[ct-vulkan] GPU=%s api=%u.%u.%u graphics-queue=%u",prop.deviceName,
                    VK_API_VERSION_MAJOR(prop.apiVersion),VK_API_VERSION_MINOR(prop.apiVersion),
                    VK_API_VERSION_PATCH(prop.apiVersion),family);
                return true;
            }
        }
        LOG("[ct-vulkan] no suitable graphics device"); return false;
    }
    uint32_t memory_type(uint32_t bits,VkMemoryPropertyFlags flags) {
        for (uint32_t i=0;i<memory.memoryTypeCount;++i)
            if ((bits&(1u<<i)) && (memory.memoryTypes[i].propertyFlags&flags)==flags) return i;
        fatal("[ct-vulkan] required memory type unavailable (flags=%X)",flags);
    }
};
std::mutex device_guard;
std::unique_ptr<Device> gpu;
void check(VkResult result,const char* operation) {
    if (result!=VK_SUCCESS) { LOG("[ct-stop] %s failed: %d",operation,result); std::_Exit(81); }
}
struct Resources {
    Device& gpu;
    VkImage image=VK_NULL_HANDLE;
    VkBuffer buffer=VK_NULL_HANDLE;
    VkDeviceMemory image_memory=VK_NULL_HANDLE,buffer_memory=VK_NULL_HANDLE;
    VkCommandPool pool=VK_NULL_HANDLE;
    VkFence fence=VK_NULL_HANDLE;
    ~Resources() {
        if (fence) gpu.proc<PFN_vkDestroyFence>("vkDestroyFence")(gpu.device,fence,nullptr);
        if (pool) gpu.proc<PFN_vkDestroyCommandPool>("vkDestroyCommandPool")(gpu.device,pool,nullptr);
        if (buffer) gpu.proc<PFN_vkDestroyBuffer>("vkDestroyBuffer")(gpu.device,buffer,nullptr);
        if (image) gpu.proc<PFN_vkDestroyImage>("vkDestroyImage")(gpu.device,image,nullptr);
        if (buffer_memory) gpu.proc<PFN_vkFreeMemory>("vkFreeMemory")(gpu.device,buffer_memory,nullptr);
        if (image_memory) gpu.proc<PFN_vkFreeMemory>("vkFreeMemory")(gpu.device,image_memory,nullptr);
    }
};
}

bool ct_gpu_initialize() {
    std::lock_guard<std::mutex> lock(device_guard);
    if (gpu) return true;
    auto next=std::make_unique<Device>();
    if (!next->initialize()) return false;
    gpu=std::move(next); return true;
}
int ct_vulkan_probe() {
    bool ok=ct_gpu_initialize();
    LOG("[ct-vulkan] instance/device probe %s; game renderer not tested",ok?"PASS":"FAIL");
    return ok?0:1;
}
int ct_vulkan_clear_test() {
    if (!ct_gpu_initialize()) return 1;
    std::lock_guard<std::mutex> lock(device_guard);
    auto& d=*gpu;
    Resources r{d};
    constexpr uint32_t width=16,height=16,bytes=width*height*4;
    VkImageCreateInfo image{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
    image.imageType=VK_IMAGE_TYPE_2D; image.format=VK_FORMAT_R8G8B8A8_UNORM;
    image.extent={width,height,1}; image.mipLevels=1; image.arrayLayers=1;
    image.samples=VK_SAMPLE_COUNT_1_BIT; image.tiling=VK_IMAGE_TILING_OPTIMAL;
    image.usage=VK_IMAGE_USAGE_TRANSFER_DST_BIT|VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
    image.sharingMode=VK_SHARING_MODE_EXCLUSIVE; image.initialLayout=VK_IMAGE_LAYOUT_UNDEFINED;
    check(d.proc<PFN_vkCreateImage>("vkCreateImage")(d.device,&image,nullptr,&r.image),"vkCreateImage");
    VkMemoryRequirements requirement{};
    d.proc<PFN_vkGetImageMemoryRequirements>("vkGetImageMemoryRequirements")(d.device,r.image,&requirement);
    VkMemoryAllocateInfo alloc{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
    alloc.allocationSize=requirement.size; alloc.memoryTypeIndex=d.memory_type(requirement.memoryTypeBits,0);
    check(d.proc<PFN_vkAllocateMemory>("vkAllocateMemory")(d.device,&alloc,nullptr,&r.image_memory),"image memory");
    check(d.proc<PFN_vkBindImageMemory>("vkBindImageMemory")(d.device,r.image,r.image_memory,0),"image binding");
    VkBufferCreateInfo buffer{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
    buffer.size=bytes; buffer.usage=VK_BUFFER_USAGE_TRANSFER_DST_BIT; buffer.sharingMode=VK_SHARING_MODE_EXCLUSIVE;
    check(d.proc<PFN_vkCreateBuffer>("vkCreateBuffer")(d.device,&buffer,nullptr,&r.buffer),"vkCreateBuffer");
    d.proc<PFN_vkGetBufferMemoryRequirements>("vkGetBufferMemoryRequirements")(d.device,r.buffer,&requirement);
    alloc.allocationSize=requirement.size;
    alloc.memoryTypeIndex=d.memory_type(requirement.memoryTypeBits,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
    check(d.proc<PFN_vkAllocateMemory>("vkAllocateMemory")(d.device,&alloc,nullptr,&r.buffer_memory),"readback memory");
    check(d.proc<PFN_vkBindBufferMemory>("vkBindBufferMemory")(d.device,r.buffer,r.buffer_memory,0),"buffer binding");
    VkCommandPoolCreateInfo pool{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO}; pool.queueFamilyIndex=d.queue_family;
    check(d.proc<PFN_vkCreateCommandPool>("vkCreateCommandPool")(d.device,&pool,nullptr,&r.pool),"command pool");
    VkCommandBufferAllocateInfo command_info{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
    command_info.commandPool=r.pool; command_info.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY; command_info.commandBufferCount=1;
    VkCommandBuffer command{};
    check(d.proc<PFN_vkAllocateCommandBuffers>("vkAllocateCommandBuffers")(d.device,&command_info,&command),"command buffer");
    VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO}; begin.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    check(d.proc<PFN_vkBeginCommandBuffer>("vkBeginCommandBuffer")(command,&begin),"begin command");
    VkImageMemoryBarrier barrier{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};
    barrier.oldLayout=VK_IMAGE_LAYOUT_UNDEFINED; barrier.newLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    barrier.srcQueueFamilyIndex=barrier.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;
    barrier.image=r.image; barrier.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};
    barrier.dstAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;
    auto pipeline_barrier=d.proc<PFN_vkCmdPipelineBarrier>("vkCmdPipelineBarrier");
    pipeline_barrier(command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,0,nullptr,1,&barrier);
    VkClearColorValue red{}; red.float32[0]=red.float32[3]=1;
    d.proc<PFN_vkCmdClearColorImage>("vkCmdClearColorImage")(command,r.image,VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,&red,1,&barrier.subresourceRange);
    barrier.oldLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL; barrier.newLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
    barrier.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT; barrier.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT;
    pipeline_barrier(command,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,0,nullptr,1,&barrier);
    VkBufferImageCopy copy{}; copy.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1}; copy.imageExtent={width,height,1};
    d.proc<PFN_vkCmdCopyImageToBuffer>("vkCmdCopyImageToBuffer")(command,r.image,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,r.buffer,1,&copy);
    VkBufferMemoryBarrier host{VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER};
    host.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT; host.dstAccessMask=VK_ACCESS_HOST_READ_BIT;
    host.srcQueueFamilyIndex=host.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED; host.buffer=r.buffer; host.offset=0; host.size=bytes;
    pipeline_barrier(command,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,0,nullptr,1,&host,0,nullptr);
    check(d.proc<PFN_vkEndCommandBuffer>("vkEndCommandBuffer")(command),"end command");
    VkFenceCreateInfo fence{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
    check(d.proc<PFN_vkCreateFence>("vkCreateFence")(d.device,&fence,nullptr,&r.fence),"fence");
    VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO}; submit.commandBufferCount=1; submit.pCommandBuffers=&command;
    check(d.proc<PFN_vkQueueSubmit>("vkQueueSubmit")(d.queue,1,&submit,r.fence),"queue submit");
    check(d.proc<PFN_vkWaitForFences>("vkWaitForFences")(d.device,1,&r.fence,VK_TRUE,5000000000ull),"fence wait");
    void* mapped=nullptr;
    check(d.proc<PFN_vkMapMemory>("vkMapMemory")(d.device,r.buffer_memory,0,bytes,0,&mapped),"readback map");
    auto data=static_cast<const uint8_t*>(mapped);
    uint32_t matched=0;
    for (uint32_t i=0;i<width*height;++i)
        if (data[4*i]==255 && data[4*i+1]==0 && data[4*i+2]==0 && data[4*i+3]==255) ++matched;
    d.proc<PFN_vkUnmapMemory>("vkUnmapMemory")(d.device,r.buffer_memory);
    LOG("[ct-vulkan] synthetic clear/readback %s: %u/%u RGBA pixels matched; not a game frame",
        matched==width*height?"PASS":"FAIL",matched,width*height);
    return matched==width*height?0:1;
}

void ct_gpu_wait_idle() {
    std::lock_guard<std::mutex> lock(device_guard);
    if (gpu) check(gpu->proc<PFN_vkDeviceWaitIdle>("vkDeviceWaitIdle")(gpu->device),"GPU synchronization");
}
