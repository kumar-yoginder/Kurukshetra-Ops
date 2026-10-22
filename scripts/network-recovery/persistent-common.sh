#!/bin/sh
# Managed by Kurukshetra-Ops network-recovery v1
# Sourced only by the reviewed installation/removal scripts.
unit=kurukshetra-network-recovery.service
unit_file=/etc/systemd/system/$unit
marker='# Managed by Kurukshetra-Ops network-recovery v1'
require_root() {
    [ "$(id -u)" = 0 ] || { echo 'Run locally with sudo after reviewing this script.' >&2; exit 1; }
}
check_unit_ownership() {
    if [ -e "$unit_file" ] || [ -L "$unit_file" ]; then
        [ ! -L "$unit_file" ] && [ "$(head -n 1 "$unit_file")" = "$marker" ] || {
            echo 'Refusing to overwrite/remove an unrelated persistent unit.' >&2; exit 1;
        }
    fi
    fragment=$(systemctl show "$unit" -p FragmentPath --value 2>/dev/null || true)
    case "$fragment" in
        ''|"$unit_file"|/run/systemd/transient/kurukshetra-network-recovery.service) ;;
        *) echo 'Unexpected loaded service unit; refusing changes.' >&2; exit 1;;
    esac
}
stop_owned_trial_timer() {
    # Discover only our simulation rollback family; leave Ethernet-up restore jobs alone.
    discovery=$(systemctl list-units --all --plain --no-legend --no-pager \
        'kurukshetra-network-test-rollback-*') || { echo 'Cannot inspect existing rollback jobs.' >&2; exit 1; }
    discovered=$(printf '%s\n' "$discovery" | awk '{print $1}')
    bases=kurukshetra-network-recovery-rollback
    for candidate in $discovered; do
        case "$candidate" in
            *.timer) candidate=${candidate%.timer};;
            *.service) candidate=${candidate%.service};;
            *) continue;;
        esac
        suffix=${candidate#kurukshetra-network-test-rollback-}
        case "$suffix" in ''|*[!0-9]*) echo 'Unexpected simulation rollback name; refusing changes.' >&2; exit 1;; esac
        bases="$bases
$candidate"
    done
    bases=$(printf '%s\n' "$bases" | sort -u)
    owned_timers=
    owned_services=
    # Validate every discovered timer AND its paired service before stopping anything.
    for trial_base in $bases; do
        for kind in timer service; do
            trial=$trial_base.$kind
            fragment=$(systemctl show "$trial" -p FragmentPath --value 2>/dev/null || true)
            case "$fragment" in
                '') continue;;
                /run/systemd/transient/"$trial") ;;
                *) echo 'Unexpected rollback unit; refusing changes.' >&2; exit 1;;
            esac
            if [ "$kind" = timer ]; then
                owned_timers="$owned_timers $trial"
                target=$(systemctl show "$trial" -p Unit --value)
                [ "$target" = "$trial_base.service" ] || { echo 'Unexpected rollback timer target.' >&2; exit 1; }
                service_fragment=$(systemctl show "$trial_base.service" -p FragmentPath --value)
                [ "$service_fragment" = "/run/systemd/transient/$trial_base.service" ] || { echo 'Rollback service ownership missing.' >&2; exit 1; }
            else
                owned_services="$owned_services $trial"
                execution=$(systemctl show "$trial" -p ExecStart --value)
                case "$execution" in
                    *'path=/usr/local/sbin/kurukshetra-network-recovery-rollback ; argv[]=/usr/local/sbin/kurukshetra-network-recovery-rollback ;'*) ;;
                    *) echo 'Unexpected rollback command; refusing changes.' >&2; exit 1;;
                esac
            fi
        done
    done
    # All timers stop first, then services: fail closed if stopping a known timer fails.
    for trial in $owned_timers; do
        systemctl stop "$trial"
    done
    for trial in $owned_services; do
        systemctl stop "$trial"
        systemctl reset-failed "$trial" 2>/dev/null || true
    done
}
