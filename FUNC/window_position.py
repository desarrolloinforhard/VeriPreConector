from core.ui.responsive import center_toplevel_in_workarea


def center_window(root, width, height):
    center_toplevel_in_workarea(root, width, height)


# For toplevel window
def place_window_bottom_right(master, child, width, height, padx=20, pady=20):
    master.update()
    master_width = master.winfo_width()
    master_height = master.winfo_height()

    master_x = master.winfo_rootx()
    master_y = master.winfo_rooty()

    window_width = master_x + master_width - width - padx
    window_height = master_y + master_height - height - pady
    child.geometry(f"{width}x{height}+{window_width}+{window_height}")


def place_frame(master, frame, horizontal="right", vertical="bottom", padx=20, pady=20):
    master_width = master.winfo_width()
    master_height = master.winfo_height()

    frame_width = frame.winfo_reqwidth()
    frame_height = frame.winfo_reqheight()

    frame_x = 20 if horizontal == "left" else master_width - frame_width - padx
    frame_y = 20 if vertical == "top" else master_height - frame_height - pady

    frame.place(x=frame_x, y=frame_y)
