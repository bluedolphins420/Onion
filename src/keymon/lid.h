#ifndef KEYMON_LID_H__
#define KEYMON_LID_H__

#include <stdint.h>
#include <stdbool.h>
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

static inline int lid_read(void)
{
    FILE *fp = fopen(LID_SENSOR_PATH, "r");
    if (!fp)
        return -1;
    int value = fgetc(fp);
    fclose(fp);
    return value == '0' ? 0 : value == '1' ? 1 : -1;
}

/* Invalid reads interrupt debounce but never invent a lid transition. */
static inline int lid_update(LidState *state, int value, uint32_t now)
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

/* An already-open lid must not cancel ordinary power-button standby. */
static inline bool lid_should_wake(const LidState *state, bool *closed_seen)
{
    if (state->stable == 0)
        *closed_seen = true;
    return *closed_seen && state->stable == 1 && state->candidate == 1;
}

static inline bool lid_sleep_expired(int timeout, uint32_t start, uint32_t now)
{
    return timeout >= 0 && now - start >= (uint32_t)timeout;
}

/* Use elapsed time, not the number of polls: input must not extend sleep. */
static inline int lid_sleep_poll_timeout(int timeout, uint32_t start, uint32_t now)
{
    if (timeout < 0)
        return LID_POLL_MS;
    uint32_t elapsed = now - start;
    if (elapsed >= (uint32_t)timeout)
        return 0;
    uint32_t remaining = (uint32_t)timeout - elapsed;
    return remaining < LID_POLL_MS ? (int)remaining : LID_POLL_MS;
}

#endif
