#ifndef KEYMON_LID_H__
#define KEYMON_LID_H__

#include <stdint.h>
#include <stdio.h>

/* Mini Flip hall sensor: 0 = closed, 1 = open. Older models lack this file. */
#define LID_SENSOR_PATH "/sys/devices/soc0/soc/soc:hall-mh248/hallvalue"
#define LID_POLL_MS 100
#define LID_DEBOUNCE_MS 200

typedef struct {
    int stable;
    int candidate;
    uint32_t since;
} LidState;

static LidState lid = {-1, -1, 0};

static int lid_read(void)
{
    FILE *fp = fopen(LID_SENSOR_PATH, "r");
    if (!fp)
        return -1;
    int value = fgetc(fp);
    fclose(fp);
    return value == '0' ? 0 : value == '1' ? 1 : -1;
}

/* Invalid reads interrupt debounce but never invent a lid transition. */
static int lid_update(LidState *state, int value, uint32_t now)
{
    if (value != 0 && value != 1) {
        state->candidate = -1;
        return 0;
    }
    if (value != state->candidate) {
        state->candidate = value;
        state->since = now;
        return 0;
    }
    if (value != state->stable && now - state->since >= LID_DEBOUNCE_MS) {
        state->stable = value;
        return 1;
    }
    return 0;
}

#endif
