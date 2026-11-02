# shellcheck shell=bash
# Sourced by Dictation's install.sh and status.sh (after lib/common.sh): the button DICTATE_BUTTON
# names, in words, for their messages (dictate-button's BUTTONS has the same values).

# dictate_button: DICTATE_BUTTON as dictate-button reads it (the last setting wins; one it doesn't
# know, or none, is menu, the default).
dictate_button() {
    local b
    b=$(sed -n "s/^[[:space:]]*\(export[[:space:]]\{1,\}\)\{0,1\}DICTATE_BUTTON=[\"']\{0,1\}\([A-Za-z_]*\).*/\2/p" \
        "$HOME/.config/frame-tweaks/dictate.conf" 2>/dev/null | tail -1 | tr '[:upper:]' '[:lower:]')
    case $b in
        menu|y|view|dpad_up|a|b|x|dpad_down|dpad_left|dpad_right|bumper_left|bumper_right|trigger_left|\
trigger_right|grip_left|grip_right|stick_left|stick_right|aux|off) echo "$b" ;;
        *) echo menu ;;
    esac
}

# button_name VALUE: that button in words ("Menu on the right controller").
button_name() {
    case $1 in
        menu) t 'Menu on the right controller' ;;
        y) t 'Y on the right controller' ;;
        view) t 'View on the left controller' ;;
        dpad_up) t 'd-pad up on the left controller' ;;
        a) t 'A on the right controller' ;;
        b) t 'B on the right controller' ;;
        x) t 'X on the right controller' ;;
        dpad_down) t 'd-pad down on the left controller' ;;
        dpad_left) t 'd-pad left on the left controller' ;;
        dpad_right) t 'd-pad right on the left controller' ;;
        bumper_left) t 'the left bumper' ;;
        bumper_right) t 'the right bumper' ;;
        trigger_left) t 'the left trigger' ;;
        trigger_right) t 'the right trigger' ;;
        grip_left) t 'the left grip' ;;
        grip_right) t 'the right grip' ;;
        stick_left) t 'the left stick (pressed in)' ;;
        stick_right) t 'the right stick (pressed in)' ;;
        aux) t 'Aux on the headset' ;;
        *) t 'Menu on the right controller' ;;
    esac
}
