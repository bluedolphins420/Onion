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
    return 0;
}
