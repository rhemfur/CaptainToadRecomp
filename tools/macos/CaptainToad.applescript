-- Captain Toad Treasure Tracker.app (tools/build_game_macos.sh compiles this with osacompile).
-- The first start, or a start with Shift held, asks for your own base game and update and prepares
-- the game in the data folder next to the app (tools/setup_game_macos.sh); later starts launch it.
use AppleScript version "2.7"
use framework "AppKit"
use scripting additions

property repoDir : "@REPO@"
property toolPath : "@PATH@"
property pythonPath : "@PYTHON@"

on run
	set appFolder to do shell script "dirname " & quoted form of POSIX path of (path to me)
	set dataDir to appFolder & "/data"
	set shiftDown to (((current application's NSEvent's modifierFlags()) as integer) div 131072) mod 2 = 1
	set gameExe to dataDir & "/bin/Captain Toad Treasure Tracker.app/Contents/MacOS/Captain Toad Treasure Tracker"
	set ready to (do shell script "test -x " & quoted form of gameExe & " && test -f " & quoted form of (dataDir & "/game/code/Kinopio.rpx") & " && echo yes || echo no") is "yes"
	if shiftDown or not ready then
		if not runSetup(dataDir) then return
	end if
	-- WWHD_USER_DIR: portable mode, settings and caches in data/user (tools/build_runtime_macos.sh)
	do shell script "cd " & quoted form of dataDir & " && WWHD_USER_DIR=" & quoted form of (dataDir & "/user") & " nohup " & quoted form of gameExe & " --game " & quoted form of (dataDir & "/game") & " --save " & quoted form of (dataDir & "/save") & " > /dev/null 2>&1 &"
end run

on pickSource(label)
	set answer to display dialog "Choose your Captain Toad " & label & ": an extracted folder (with code, content and meta) or a .rar, .zip or .7z archive of one." buttons {"Cancel", "Archive…", "Folder…"} default button 3 cancel button 1 with title "Captain Toad: Treasure Tracker setup"
	if button returned of answer is "Folder…" then
		return POSIX path of (choose folder with prompt "Captain Toad " & label & " folder")
	end if
	return POSIX path of (choose file with prompt "Captain Toad " & label & " archive" of type {"com.rarlab.rar-archive", "public.zip-archive", "org.7-zip.7-zip-archive", "rar", "zip", "7z"})
end pickSource

on runSetup(dataDir)
	-- tools/setup_game_macos.sh holds this lock while it runs (also when started from a terminal)
	set lockPid to do shell script "cat " & quoted form of (dataDir & "/setup.lock/pid") & " 2>/dev/null || true"
	if lockPid is not "" then
		if (do shell script "kill -0 " & lockPid & " 2>/dev/null && echo running || echo done") is "running" then
			display dialog "A setup is already running. Start Captain Toad: Treasure Tracker again when it has finished." buttons {"OK"} default button 1 with title "Captain Toad: Treasure Tracker setup" with icon caution
			return false
		end if
	end if
	display dialog "Captain Toad: Treasure Tracker prepares the game once from your own base game and v16 update (USA or Europe): it translates the game code and compiles it on this Mac, which takes several minutes. Hold Shift while starting it to run this setup again." buttons {"Cancel", "Continue"} default button 2 cancel button 1 with title "Captain Toad: Treasure Tracker setup"
	set basePath to pickSource("base game")
	set updatePath to pickSource("update (v16)")
	set logFile to dataDir & "/setup.log"
	set statusFile to dataDir & "/setup-status"
	set pid to do shell script "mkdir -p " & quoted form of dataDir & " && rm -f " & quoted form of statusFile & " && PATH=" & quoted form of toolPath & " PYTHON=" & quoted form of pythonPath & " nohup /bin/sh " & quoted form of (repoDir & "/tools/setup_game_macos.sh") & " " & quoted form of dataDir & " " & quoted form of basePath & " " & quoted form of updatePath & " > " & quoted form of logFile & " 2>&1 & echo $!"
	set progress total steps to 5
	set progress completed steps to 0
	set progress description to "Preparing Captain Toad: Treasure Tracker"
	set progress additional description to "Starting"
	try
		repeat while (do shell script "kill -0 " & pid & " 2>/dev/null && echo running || echo done") is "running"
			set statusLine to do shell script "cat " & quoted form of statusFile & " 2>/dev/null || true"
			if statusLine is not "" then
				set progress completed steps to ((character 1 of statusLine) as integer) - 1
				set progress additional description to text 5 thru -1 of statusLine
			end if
			delay 1
		end repeat
	on error number -128
		-- Stop in the progress window: end the setup and everything it started
		do shell script "kt() { for c in $(pgrep -P $1); do kt $c; done; kill $1 2>/dev/null; }; kt " & pid & "; true"
		return false
	end try
	set exitCode to do shell script "cat " & quoted form of (dataDir & "/setup-exit") & " 2>/dev/null || echo 1"
	if exitCode is not "0" then
		set tailText to do shell script "tail -n 12 " & quoted form of logFile
		set answer to display dialog "Setup did not finish:" & return & return & tailText buttons {"Show log", "OK"} default button 2 with title "Captain Toad: Treasure Tracker setup" with icon stop
		if button returned of answer is "Show log" then do shell script "open -e " & quoted form of logFile
		return false
	end if
	set progress completed steps to 5
	return true
end runSetup
