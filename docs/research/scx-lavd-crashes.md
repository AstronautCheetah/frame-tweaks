# scx_lavd failures on SteamOS 0.5.8 (Steam Frame)

SteamOS runs the Frame's CPUs through sched_ext with scx_lavd 1.1.2 (`scx.service`, flags from
`/etc/default/scx`: `--pinned-slice-us 500 --lb-local-dsq-util-pct 0`). Its BPF code fails now
and then while a new task is being set up, and the kernel switches it off:

```
kernel: sched_ext: BPF scheduler "lavd_1.1.2_aarch64_unknown_linux_gnu" disabled (scx_bpf_error)
kernel: sched_ext: lavd_1.1.2_aarch64_unknown_linux_gnu: src/bpf/main.bpf.c:2214: task_ctx_stor first lookup failed
kernel:    bpf_prog_..._lavd_init_task ... __scx_init_task ... scx_fork ... copy_process ... clone3
```

systemd restarts the service (`Restart=on-failure`, `StartLimitBurst=2` in 30 s), and the kernel's
own scheduler runs in between. The task being created at that moment, and sometimes the task on
the CPU, don't survive the switch.

## Seen on one Frame, SteamOS build 20261106.6144341

| When | Creating a task for | What died |
|---|---|---|
| 2026-11-04 | VLC (Flatpak), launched for a test | the VR session restarted |
| 2026-11-09 16:21:39 | Signal (Flatpak) | nothing visible; service restart 1 |
| 2026-11-09 16:25:17 | (RoomViewProcess and vrserver on the CPUs) | nothing visible; restart 2 |
| 2026-11-09 16:37:58 | Datcord (Flatpak); gamescope-xwm on the CPU | vrclient's compositor pipe timed out, vrcompositor's watchdog aborted it 21 s later (SIGABRT, minidumps bp-ab55a6e3 and bp-d1cc906b), SteamVR and gamescope-wl restarted; VLC segfaulted in the restart |
| 2026-11-10 10:26:18 | scrcpy's threads (Android Mirror) | scrcpy ended after 1.4 s with no error of its own; the second try worked |

Memory wasn't a factor in any (plenty free; the cgroup limits of VR memory guard untouched).
The common thread is process or thread creation under load: an app launch, a tool spawning
helpers.

## Workarounds

- **Stock CPU scheduler** (Attic, `stock-scheduler`): `systemctl mask --now scx.service`, kept
  across SteamOS updates through `/etc/atomic-update.conf.d`. Stopping scx_lavd is clean (it
  unregisters and the kernel's EEVDF takes over); no restart needed. The cost to judge: Valve
  tuned scx_lavd for the Frame's fast and slow cores and its VR threads.
- No other sched_ext scheduler ships in SteamOS 0.5.8's `scx-scheds` package, so
  `SCX_SCHEDULER_OVERRIDE` (which `scx.service` honours) has nothing to point at.

## Report

Worth a SteamOS bug report with the kernel lines above, the times, and the two SteamVR crash
IDs, which Valve's crash service already holds. A fixed scx_lavd (newer than 1.1.2) ends the
need for the workaround.
