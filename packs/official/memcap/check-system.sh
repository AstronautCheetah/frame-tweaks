#!/bin/bash
# The caps need systemd to delegate the memory controller to the user manager.
f=/sys/fs/cgroup/user.slice/user-$(id -u).slice/user@$(id -u).service/cgroup.controllers
grep -qw memory "$f" 2>/dev/null && echo "memory controller delegated to user services" && exit 0
echo "memory controller not delegated (cgroup.controllers: $(cat "$f" 2>/dev/null))"; exit 1
