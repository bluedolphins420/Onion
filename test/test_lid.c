#include <assert.h>
#include "../src/keymon/lid.h"

int main(void)
{
    LidState state = {-1, -1, 0};
    assert(!lid_update(&state, 1, 0));
    assert(!lid_update(&state, 1, 199));
    assert(lid_update(&state, 1, 200));
    assert(state.stable == 1);

    // A brief sensor bounce must not suspend the device.
    assert(!lid_update(&state, 0, 300));
    assert(!lid_update(&state, 1, 400));
    assert(!lid_update(&state, 1, 600));
    assert(state.stable == 1);
    assert(!lid_update(&state, 0, 700));
    assert(lid_update(&state, 0, 900));
    assert(state.stable == 0);

    // A read failure breaks debounce, without changing the last stable state.
    assert(!lid_update(&state, 1, 1000));
    assert(!lid_update(&state, -1, 1200));
    assert(state.stable == 0);
    assert(!lid_update(&state, 1, 1300));
    assert(!lid_update(&state, 1, 1499));
    assert(lid_update(&state, 1, 1500));

    // Monotonic millisecond counter wraparound remains safe.
    state = (LidState){1, 1, 0};
    assert(!lid_update(&state, 0, UINT32_MAX - 99));
    assert(!lid_update(&state, 0, 99));
    assert(lid_update(&state, 0, 100));
    assert(state.stable == 0);

    // Power-button standby with an open lid must stay asleep until close/open.
    bool closed_seen = false;
    state = (LidState){1, 1, 0};
    assert(!lid_should_wake(&state, &closed_seen));
    lid_update(&state, 0, 0);
    lid_update(&state, 0, 200);
    assert(!lid_should_wake(&state, &closed_seen));
    assert(closed_seen);
    lid_update(&state, 1, 300);
    assert(!lid_should_wake(&state, &closed_seen));
    lid_update(&state, -1, 500);
    assert(!lid_should_wake(&state, &closed_seen));
    lid_update(&state, 1, 600);
    lid_update(&state, 1, 800);
    assert(lid_should_wake(&state, &closed_seen));

    // Repeated early poll returns never restart the six-minute countdown.
    uint32_t start = 1000;
    for (uint32_t now = start; now < start + 360000; now += 17) {
        assert(!lid_sleep_expired(360000, start, now));
        assert(lid_sleep_poll_timeout(360000, start, now) <= LID_POLL_MS);
    }
    assert(lid_sleep_poll_timeout(360000, start, start + 359990) == 10);
    assert(lid_sleep_poll_timeout(360000, start, start + 360000) == 0);
    assert(lid_sleep_expired(360000, start, start + 360000));
    assert(!lid_sleep_expired(-1, start, start + 360000));
    assert(lid_sleep_poll_timeout(-1, start, start + 360000) == LID_POLL_MS);
    assert(lid_sleep_expired(0, start, start));
    assert(!lid_sleep_expired(200, UINT32_MAX - 99, 99));
    assert(lid_sleep_expired(200, UINT32_MAX - 99, 100));
    return 0;
}
