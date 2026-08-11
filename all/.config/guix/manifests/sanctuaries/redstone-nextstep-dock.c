#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <stdlib.h>
#include <string.h>

static const char *cube[] = {
    "                                                ",
    "                                                ",
    "                                                ",
    "                                                ",
    "                                                ",
    "                       ..                       ",
    "                     ......                     ",
    "                    ..++++..                    ",
    "                  ..++++++++..                  ",
    "                ..++++++++++++..                ",
    "              ...@@@@@@@@@@@@@@...              ",
    "            ...+@@@@@@@@@@@@@@@@@...            ",
    "           ..+++@@@@@@@@@@@@@@@@@@@..           ",
    "         ..+++++@@@@@@@@@@@@@@@@@@@@@..         ",
    "        ...+++++@@@@@@@@@@@@@@@@@@@@@...        ",
    "        .....+++@@@@@@@@@@@@@@@@@@@.....        ",
    "        .#.....+@@@@@@@@@@@@@@@@@.....$.        ",
    "        .###.....@@@@@@@@@@@@@@.....$$$.        ",
    "        .####@....@@@@@@@@@@@@....$$$$$.        ",
    "        .####@@.....@@@@@@@@.....$$$$$$.        ",
    "        .####@@@@.....@@@@.....$$$$$$$$.        ",
    "        .####@@@@@@..........$$$$$$$$$$.        ",
    "        .####@@@@@@@@......$$$$$$$$$$$$.        ",
    "        .####@@@@@@@@@@..$$$$$$$$$$$$$$.        ",
    "        .####@@@@@@@@@@..$$$$$$$$$$$$$$.        ",
    "        .####@@@@@@@@@@..$$$$$$$$$$$$$$.        ",
    "        .####@@@@@@@@@@..$$&&&$$$&&$$$$.        ",
    "        .####@@@@@@@@@@..$$&&&$$$&&$$$$.        ",
    "        .####@@@@@@@@@@..$$&&&&$$&&$$$$.        ",
    "        .####@@@@@@@@@@..$$&&&&$$&&$$$$.        ",
    "        .####@@@@@@@@@@..$$&&$&&$&&$$$$.        ",
    "        .####@@@@@@@@@@..$$&&$&&$&&$$$$.        ",
    "        .####@@@@@@@@@@..$$&&$$&&&&$$$$.        ",
    "        .####@@@@@@@@@@..$$&&$$&&&&$$$$.        ",
    "        .####@@@@@@@@@@..$$&&$$$&&&$$$$.        ",
    "         ..##@@@@@@@@@@..$$&&$$$$&&$$..         ",
    "           ..@@@@@@@@@@..$$$$$$$$$$..           ",
    "            ...@@@@@@@@..$$$$$$$$...            ",
    "              ...@@@@@@..$$$$$$...              ",
    "                ..@@@@@..$$$$$..                ",
    "                  ..@@@..$$$..                  ",
    "                    ..@..$..                    ",
    "                     ......                     ",
    "                       ..                       ",
    "                                                ",
    "                                                ",
    "                                                ",
    "                                                "
};

static unsigned long named_pixel(Display *display, int screen, const char *name) {
    XColor exact;
    XColor allocated;
    Colormap colormap = DefaultColormap(display, screen);
    if (XAllocNamedColor(display, colormap, name, &allocated, &exact))
        return allocated.pixel;
    return BlackPixel(display, screen);
}

static void draw(Display *display, Window window, GC gc, int screen) {
    unsigned long black = BlackPixel(display, screen);
    unsigned long white = WhitePixel(display, screen);
    unsigned long colours[256] = {0};
    colours[(unsigned char)'.'] = named_pixel(display, screen, "#05070A");
    colours[(unsigned char)'+'] = named_pixel(display, screen, "#E6EBEE");
    colours[(unsigned char)'@'] = named_pixel(display, screen, "#AAB5BC");
    colours[(unsigned char)'#'] = named_pixel(display, screen, "#77838C");
    colours[(unsigned char)'$'] = named_pixel(display, screen, "#2C373F");
    colours[(unsigned char)'&'] = white;
    XSetForeground(display, gc, black);
    XFillRectangle(display, window, gc, 0, 0, 64, 64);
    XSetForeground(display, gc, white);
    XDrawRectangle(display, window, gc, 1, 1, 61, 61);
    for (int y = 0; y < 48; ++y) {
        for (int x = 0; x < 48; ++x) {
            unsigned char code = (unsigned char)cube[y][x];
            if (code == ' ') continue;
            XSetForeground(display, gc, colours[code]);
            XDrawPoint(display, window, gc, x + 8, y + 8);
        }
    }
}

int main(void) {
    Display *display = XOpenDisplay(NULL);
    if (!display) return 1;
    int screen = DefaultScreen(display);
    Window root = RootWindow(display, screen);
    Window main_window = XCreateSimpleWindow(display, root, 0, 0, 1, 1, 0,
                                              BlackPixel(display, screen),
                                              BlackPixel(display, screen));
    Window icon_window = XCreateSimpleWindow(display, root, 0, 0, 64, 64, 0,
                                              WhitePixel(display, screen),
                                              BlackPixel(display, screen));
    XClassHint class_hint = {"nextstep-dock", "DockApp"};
    XSetClassHint(display, main_window, &class_hint);
    XStoreName(display, main_window, "NeXT");
    XWMHints hints;
    memset(&hints, 0, sizeof(hints));
    hints.flags = StateHint | IconWindowHint | WindowGroupHint;
    hints.initial_state = WithdrawnState;
    hints.icon_window = icon_window;
    hints.window_group = main_window;
    XSetWMHints(display, main_window, &hints);
    XSelectInput(display, icon_window, ExposureMask | StructureNotifyMask);
    XMapWindow(display, main_window);
    GC gc = XCreateGC(display, icon_window, 0, NULL);
    draw(display, icon_window, gc, screen);
    for (;;) {
        XEvent event;
        XNextEvent(display, &event);
        if (event.type == Expose && event.xexpose.count == 0)
            draw(display, icon_window, gc, screen);
        if (event.type == DestroyNotify) break;
    }
    XFreeGC(display, gc);
    XCloseDisplay(display);
    return 0;
}
