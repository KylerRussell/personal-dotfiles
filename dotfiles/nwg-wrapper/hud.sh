#!/usr/bin/env bash
# Anduril HUD launcher.
# Reads hud.conf and (re)launches swaybg wallpapers + nwg-wrapper widgets per
# monitor. The telemetry/hero widgets render an ordered list of line modules
# (presets/lines/) via hud-render.sh; image/figure are single selections.
# Used at startup (exec-once) and on "Apply" from the config utility.

DIR="$HOME/.config/nwg-wrapper"
WALL="$HOME/.config/hypr/wallpapers"
CSS="$DIR/style.css"
REND="$DIR/hud-render.sh"
CONF="$DIR/hud.conf"

# Defaults (used if hud.conf is missing or incomplete)
m1_telemetry=sector,lat,lon,elev,status; m1_hero=clock,date; m1_image=globe;      m1_figure=fig1
m2_telemetry=sector,lat,lon,elev,status; m2_hero=clock,date; m2_image=citymap;    m2_figure=fig2
m3_telemetry=sector,lat,lon,elev,status; m3_hero=clock,date; m3_image=topography; m3_figure=fig3
[ -f "$CONF" ] && source "$CONF"

# Clear the running HUD first. Match "nwg-wrapper -o" (the widget invocation) so
# pkill -f doesn't also match this script's path or the config utility.
pkill -f 'nwg-wrapper -o' 2>/dev/null
pkill -x swaybg           2>/dev/null
sleep 0.5

launch() {
    local out="$1" tel="$2" hero="$3" img="$4" fig="$5"
    [ "$img" != none ] && [ -f "$WALL/$img.png" ] && \
        swaybg -o "$out" -i "$WALL/$img.png" -m fill &
    [ -n "$tel" ] && [ "$tel" != off ] && \
        HUD_SECTION=telemetry HUD_LINES="$tel" \
        nwg-wrapper -o "$out" -s "$REND" -c "$CSS" -p left  -a start -mt 90 -ml 60 -l 1 -r 5000 &
    [ -n "$hero" ] && [ "$hero" != off ] && \
        HUD_SECTION=hero HUD_LINES="$hero" \
        nwg-wrapper -o "$out" -s "$REND" -c "$CSS" -p left  -a end   -mb 90 -ml 60 -l 1 -r 5000 &
    [ "$fig" != off ] && [ -f "$DIR/presets/figure/$fig.pango" ] && \
        nwg-wrapper -o "$out" -t "$DIR/presets/figure/$fig.pango" -c "$CSS" -p right -a end -mb 28 -mr 40 -l 1 &
}

launch Virtual-1 "$m1_telemetry" "$m1_hero" "$m1_image" "$m1_figure"
launch Virtual-2 "$m2_telemetry" "$m2_hero" "$m2_image" "$m2_figure"
launch Virtual-3 "$m3_telemetry" "$m3_hero" "$m3_image" "$m3_figure"
