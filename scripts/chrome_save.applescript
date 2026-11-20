-- Load a Yahoo league URL in a Chrome tab that is already signed in, and save its HTML.
-- Usage: osascript chrome_save.applescript <url> <out.html> [wait seconds]
-- Reuses any tab already on the league (fantasysports.yahoo.com/f1/700759); if none is
-- open it adds one to the back window without bringing Chrome forward.
-- No "Allow JavaScript from Apple Events" needed: this only loads and saves.
-- Tabs are addressed by id, since index references break when another tab opens or closes.
on run argv
	set theURL to item 1 of argv
	set outPath to item 2 of argv
	set waitSecs to 20
	if (count of argv) > 2 then set waitSecs to (item 3 of argv) as integer
	tell application "Google Chrome"
		if (count of windows) is 0 then return "NO_WINDOW"
		set tid to missing value
		set wid to missing value
		repeat with w in (get every window)
			set theWid to id of w
			set theURLs to URL of every tab of window id theWid
			set theIDs to id of every tab of window id theWid
			repeat with i from 1 to count of theURLs
				if (item i of theURLs) contains "fantasysports.yahoo.com/f1/700759" then
					set tid to item i of theIDs
					set wid to theWid
					exit repeat
				end if
			end repeat
			if tid is not missing value then exit repeat
		end repeat
		if tid is missing value then
			set wid to id of last window
			set keepIdx to active tab index of window id wid
			set newTab to make new tab at end of tabs of window id wid with properties {URL:theURL}
			set tid to id of newTab
			set active tab index of window id wid to keepIdx
		else
			set URL of tab id tid of window id wid to theURL
		end if
		delay 1
		repeat waitSecs times
			if loading of tab id tid of window id wid is false then exit repeat
			delay 1
		end repeat
		set finalURL to URL of tab id tid of window id wid
		save tab id tid of window id wid in (POSIX file outPath) as "only html"
		return finalURL
	end tell
end run
