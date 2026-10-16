# Mouse cursor fix: research and decisions

For maintainers and reviewers; not shown in the app. Why [Mouse cursor fix](../../packs/third-party/cursor/)
isn't offered from SteamOS 0.5.6 (gamescope 3.16.30) on, and how that was found. Checked on 16
October 2026 on one Frame, after updating from SteamOS 0.4.5 (gamescope 3.16.28) to the 0.5.6
beta (gamescope 3.16.30).

## Decision

On gamescope 3.16.30 and later the fix isn't needed and does harm (two pointers), so its
`needed.sh` says so: Frame Tweaks hides it there, `./install.sh install` skips it, and an
installed one's status asks to uninstall it. Older SteamOS versions still get it. The check is
gamescope's version, the part that changed, not the SteamOS version.

## What changed

- **The symptom:** after the update, desktop mode showed two pointers: the fix's large one and
  a black X. Floating VR windows' pointers looked as good or better.
- **What the fix does:** `KWIN_FORCE_SW_CURSOR=1` makes KWin (the nested desktop, a window on
  gamescope's Xwayland `:0`) draw the pointer into its picture, because gamescope's VR view used
  to leave the X cursor out.
- **Gamescope 3.16.30** includes Valve's
  [865e0c1](https://github.com/ValveSoftware/gamescope/commit/865e0c1684), "OpenVRBackend:
  keep the cursor out of the composite": instead of baking the X cursor into the picture, it
  hands it to SteamVR's cursor override, which draws it, for a physical mouse ("so the pointer
  looks the same however the frame reaches the overlay"). Found by comparing the two versions
  (`gh api repos/ValveSoftware/gamescope/compare/3.16.28...3.16.30`).
- **The black X:** XFixes on `:0`, with the pointer over KWin's window, reported the X server's
  built-in cursor: 16×16, hotspot 7,7, serial 1. With the fix, KWin draws the pointer itself and
  sets no cursor on its window, so SteamVR is handed X's default, the black X. (On the nested
  Xwayland `:2`, KWin's own pointer was 96×96: the large one.)
- **Without the fix,** KWin's X11 window backend gives its window a real X cursor
  (`xcb_render_create_cursor` is in `libkwin.so.6`, KWin 6.2.5), which SteamVR then draws: one
  normal pointer. The owner removed the fix and restarted: one pointer, looking right.

The SteamOS session script (`/usr/lib/steamos/gamescope-session`, unchanged by the update)
passes `--cursor /usr/share/holo/holo-cursor.png`, a file that doesn't exist on this build;
that's gamescope's own default cursor, not the one SteamVR draws for windows.

## Revisit when

- A gamescope version is found that needs the fix again (the pointer missing in desktop mode
  without it): change `needed.sh`'s version range.
- Gamescope's version numbering changes (`needed.sh` compares with `sort -V`, ignoring the
  package release).
