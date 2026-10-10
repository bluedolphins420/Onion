#ifndef SYSTEM_H__
#define SYSTEM_H__

#include <fcntl.h>
#include <stdbool.h>

#include "clock.h"
#include "utils/flags.h"

// system directories
#define GPIO_DIR1 "/sys/class/gpio/"
#define GPIO_DIR2 "/sys/devices/gpiochip0/gpio/"
#define PWM_DIR "/sys/devices/soc0/soc/1f003400.pwm/pwm/pwmchip0/"
#define CPU_DIR "/sys/devices/system/cpu/cpufreq/policy0/"

#define CPU_SCALING_MIN_FREQ CPU_DIR "scaling_min_freq"
#define CPU_SCALING_GOVERNOR CPU_DIR "scaling_governor"

#define system_powersave_on() system_powersave(true)
#define system_powersave_off() system_powersave(false)

/**
 * @brief Creates the file `/tmp/.offOrder`,
 * which is used by `runtime.sh` for knowing when to show shutdown screen.
 *
 */
void set_system_shutdown(void)
{
    temp_flag_set(".offOrder", true);
    system_clock_get();
    system_clock_save();
    sync();
}

/**
 * @brief Toggle powersave mode
 *
 * @param enabled true: turn on powersave, false: turn off powersave
 */
void system_powersave(bool enabled)
{
    static uint32_t saved_clock_mhz, saved_min_freq;
    static char saved_governor[16];
    static bool active = false;
    FILE *fp;

    if (enabled) {
        if (active)
            return;
        char buffer[128];
        FILE *pipe = popen("cpuclock", "r");
        if (!pipe)
            return;
        saved_clock_mhz = 0;
        if (fgets(buffer, sizeof(buffer), pipe))
            sscanf(buffer, "%u", &saved_clock_mhz);
        int status = pclose(pipe);
        if (status != 0 || saved_clock_mhz < 100 || saved_clock_mhz > 2400)
            return; // Never apply a CPU state that cannot be restored.

        // save values for restoring later
        saved_governor[0] = '\0';
        saved_min_freq = UINT32_MAX;
        file_get(fp, CPU_SCALING_GOVERNOR, "%15s", saved_governor);
        file_get(fp, CPU_SCALING_MIN_FREQ, "%u", &saved_min_freq);
        if (!saved_governor[0] || saved_min_freq == UINT32_MAX)
            return;
        active = true;
        // set powersaving values
        file_put(fp, CPU_SCALING_MIN_FREQ, "%u", 0U);
        file_put(fp, CPU_SCALING_GOVERNOR, "%s", "powersave");
    }
    else {
        if (!active)
            return;
        // restore
        char sCommand[32];
        snprintf(sCommand, sizeof(sCommand), "cpuclock %u", saved_clock_mhz);
        system(sCommand);
        file_put(fp, CPU_SCALING_MIN_FREQ, "%u", saved_min_freq);
        file_put(fp, CPU_SCALING_GOVERNOR, "%s", saved_governor);
        active = false;
    }
}

#endif // SYSTEM_H__
