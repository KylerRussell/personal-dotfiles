#!/usr/bin/env bash
# Anduril HUD launcher.
# Reads hud.conf and (re)launches swaybg wallpapers + nwg-wrapper widgets per
# monitor. Used at startup (exec-once) and on "Apply" from the config utility.
# Safe to re-run: it kills the existing HUD first.

DIR="$HOME/.config/nwg-wrapper"
WALL="$HOME/.config/hypr/wallpapers"
CSS="$DIR/style.css"
CONF="$DIR/hud.conf"

# Defaults (used if hud.conf is missing or incomplete)
m1_telemetry=coordinates; m1_hero=clock24; m1_image=globe;      m1_figure=fig1
m2_telemetry=coordinates; m2_hero=clock24; m2_image=citymap;    m2_figure=fig2
m3_telemetry=coordinates; m3_hero=clock24; m3_image=topography; m3_figure=fig3
[ -f "$CONF" ] && source "$CONF"

# Clear any running HUD before relaunching
pkill -f nwg-wrapper 2>/dev/null
pkill -x swaybg     2>/dev/null
sleep 0.5

launch() {
    local out="$1" tel="$2" hero="$3" img="$4" fig="$5"
    [ "$img" != none ] && [ -f "$WALL/$img.png" ] && \
        swaybg -o "$out" -i "$WALL/$img.png" -m fill &
    [ "$tel" != off ] && [ -f "$DIR/presets/telemetry/$tel.sh" ] && \
        nwg-wrapper -o "$out" -s "$DIR/presets/telemetry/$tel.sh" -c "$CSS" -p left  -a start -mt 90 -ml 60 -l 1 -r 5000 &
    [ "$hero" != off ] && [ -f "$DIR/presets/hero/$hero.sh" ] && \
        nwg-wrapper -o "$out" -s "$DIR/presets/hero/$hero.sh"     -c "$CSS" -p left  -a end   -mb 90 -ml 60 -l 1 -r 1000 &
    [ "$fig" != off ] && [ -f "$DIR/presets/figure/$fig.pango" ] && \
        nwg-wrapper -o "$out" -t "$DIR/presets/figure/$fig.pango" -c "$CSS" -p right -a end   -mb 28 -mr 40 -l 1 &
}

launch Virtual-1 "$m1_telemetry" "$m1_hero" "$m1_image" "$m1_figure"
launch Virtual-2 "$m2_telemetry" "$m2_hero" "$m2_image" "$m2_figure"
launch Virtual-3 "$m3_telemetry" "$m3_hero" "$m3_image" "$m3_figure"
