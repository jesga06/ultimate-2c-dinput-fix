import socket
import json
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import collections

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 9999))
    sock.setblocking(False)

    history_len = 100
    times = collections.deque(maxlen=history_len)
    data_lx = collections.deque(maxlen=history_len)
    data_ly = collections.deque(maxlen=history_len)
    data_rx = collections.deque(maxlen=history_len)
    data_ry = collections.deque(maxlen=history_len)
    data_lt = collections.deque(maxlen=history_len)
    data_rt = collections.deque(maxlen=history_len)

    fig, (ax_sticks, ax_triggers) = plt.subplots(2, 1, figsize=(8, 6))
    fig.canvas.manager.set_window_title("Input Inspector Graph")

    line_lx, = ax_sticks.plot([], [], label='Left X', color='blue')
    line_ly, = ax_sticks.plot([], [], label='Left Y', color='cyan')
    line_rx, = ax_sticks.plot([], [], label='Right X', color='red')
    line_ry, = ax_sticks.plot([], [], label='Right Y', color='magenta')
    ax_sticks.set_xlim(0, history_len)
    ax_sticks.set_ylim(-1.1, 1.1)
    ax_sticks.legend(loc='upper right')
    ax_sticks.set_title("Sticks")

    line_lt, = ax_triggers.plot([], [], label='Left Trigger', color='green')
    line_rt, = ax_triggers.plot([], [], label='Right Trigger', color='orange')
    ax_triggers.set_xlim(0, history_len)
    ax_triggers.set_ylim(-0.1, 1.1)
    ax_triggers.legend(loc='upper right')
    ax_triggers.set_title("Triggers")

    plt.tight_layout()

    t_counter = 0

    def update(frame):
        nonlocal t_counter
        # Drain UDP socket
        latest_data = None
        while True:
            try:
                msg, _ = sock.recvfrom(1024)
                latest_data = json.loads(msg.decode('utf-8'))
            except BlockingIOError:
                break
            except Exception:
                break

        if latest_data:
            times.append(t_counter)
            t_counter += 1
            data_lx.append(latest_data.get('lx', 0.0))
            data_ly.append(latest_data.get('ly', 0.0))
            data_rx.append(latest_data.get('rx', 0.0))
            data_ry.append(latest_data.get('ry', 0.0))
            data_lt.append(latest_data.get('lt', 0.0))
            data_rt.append(latest_data.get('rt', 0.0))
            
            x_data = list(range(len(times)))
            line_lx.set_data(x_data, list(data_lx))
            line_ly.set_data(x_data, list(data_ly))
            line_rx.set_data(x_data, list(data_rx))
            line_ry.set_data(x_data, list(data_ry))
            
            line_lt.set_data(x_data, list(data_lt))
            line_rt.set_data(x_data, list(data_rt))
            
            if len(times) > 0:
                ax_sticks.set_xlim(max(0, len(times) - history_len), max(history_len, len(times)))
                ax_triggers.set_xlim(max(0, len(times) - history_len), max(history_len, len(times)))

        return line_lx, line_ly, line_rx, line_ry, line_lt, line_rt

    ani = animation.FuncAnimation(fig, update, interval=20, blit=False, cache_frame_data=False)
    plt.show()

if __name__ == '__main__':
    main()
