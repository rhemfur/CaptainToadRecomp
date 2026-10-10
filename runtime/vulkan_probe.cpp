#include "runtime.h"
#ifdef __ANDROID__
#define VK_NO_PROTOTYPES
#include <vulkan/vulkan.h>
#include <dlfcn.h>
#include <vector>

int ct_vulkan_probe() {
    void* library=dlopen("libvulkan.so",RTLD_NOW|RTLD_LOCAL);
    if (!library) { LOG("[ct-vulkan] cannot load system Vulkan"); return 1; }
    auto get=reinterpret_cast<PFN_vkGetInstanceProcAddr>(dlsym(library,"vkGetInstanceProcAddr"));
    if (!get) { dlclose(library); return 1; }
    auto create=reinterpret_cast<PFN_vkCreateInstance>(get(nullptr,"vkCreateInstance"));
    VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};
    app.pApplicationName="Captain Toad runtime diagnostic";
    app.apiVersion=VK_API_VERSION_1_3;
    VkInstanceCreateInfo info{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
    info.pApplicationInfo=&app;
    VkInstance instance{};
    VkResult result=create(&info,nullptr,&instance);
    if (result!=VK_SUCCESS) { LOG("[ct-vulkan] vkCreateInstance returned %d",result); dlclose(library); return 1; }
    auto destroy=reinterpret_cast<PFN_vkDestroyInstance>(get(instance,"vkDestroyInstance"));
    auto enumerate=reinterpret_cast<PFN_vkEnumeratePhysicalDevices>(get(instance,"vkEnumeratePhysicalDevices"));
    auto properties=reinterpret_cast<PFN_vkGetPhysicalDeviceProperties>(get(instance,"vkGetPhysicalDeviceProperties"));
    auto families=reinterpret_cast<PFN_vkGetPhysicalDeviceQueueFamilyProperties>(get(instance,"vkGetPhysicalDeviceQueueFamilyProperties"));
    auto create_device=reinterpret_cast<PFN_vkCreateDevice>(get(instance,"vkCreateDevice"));
    auto device_get=reinterpret_cast<PFN_vkGetDeviceProcAddr>(get(instance,"vkGetDeviceProcAddr"));
    uint32_t count=0;
    result=enumerate(instance,&count,nullptr);
    bool ok=false;
    if (result==VK_SUCCESS && count) {
        std::vector<VkPhysicalDevice> devices(count);
        result=enumerate(instance,&count,devices.data());
        if (result==VK_SUCCESS) for (auto physical:devices) {
            VkPhysicalDeviceProperties prop{};
            properties(physical,&prop);
            LOG("[ct-vulkan] GPU=%s api=%u.%u.%u vendor=%04X driver=%u",prop.deviceName,
                VK_API_VERSION_MAJOR(prop.apiVersion),VK_API_VERSION_MINOR(prop.apiVersion),
                VK_API_VERSION_PATCH(prop.apiVersion),prop.vendorID,prop.driverVersion);
            uint32_t queues=0;
            families(physical,&queues,nullptr);
            std::vector<VkQueueFamilyProperties> queue_properties(queues);
            families(physical,&queues,queue_properties.data());
            for (uint32_t index=0;index<queues;++index) {
                if (!(queue_properties[index].queueFlags & VK_QUEUE_GRAPHICS_BIT)) continue;
                float priority=1.0f;
                VkDeviceQueueCreateInfo queue{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
                queue.queueFamilyIndex=index; queue.queueCount=1; queue.pQueuePriorities=&priority;
                VkDeviceCreateInfo device_info{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};
                device_info.queueCreateInfoCount=1; device_info.pQueueCreateInfos=&queue;
                VkDevice device{};
                result=create_device(physical,&device_info,nullptr,&device);
                LOG("[ct-vulkan] graphics queue=%u vkCreateDevice=%d",index,result);
                if (result==VK_SUCCESS) {
                    auto destroy_device=reinterpret_cast<PFN_vkDestroyDevice>(device_get(device,"vkDestroyDevice"));
                    destroy_device(device,nullptr);
                    ok=true;
                }
                break;
            }
        }
    }
    destroy(instance,nullptr);
    dlclose(library);
    LOG("[ct-vulkan] instance/device probe %s; game renderer not tested",ok?"PASS":"FAIL");
    return ok?0:1;
}
#else
int ct_vulkan_probe() { LOG("[ct-vulkan] this probe currently targets Android"); return 2; }
#endif
