# fish activation script for the sensor monitor virtual environment
set -gx VIRTUAL_ENV (realpath (status dirname)/..)
set -gx PATH $VIRTUAL_ENV/bin $PATH
set -gx VIRTUAL_ENV_PROMPT "sensor_monitor"
functions -c fish_prompt __sensor_monitor_old_fish_prompt
function fish_prompt
    echo -n "($VIRTUAL_ENV_PROMPT) "
    __sensor_monitor_old_fish_prompt
end