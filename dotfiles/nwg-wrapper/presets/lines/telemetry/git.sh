#!/usr/bin/env bash
R="$HOME/personal-dotfiles-main"
if git -C "$R" rev-parse --git-dir >/dev/null 2>&1; then
    a=$(git -C "$R" rev-list --count '@{u}..HEAD' 2>/dev/null || echo 0)
    printf '<span font="Barlow Condensed 12" foreground="#8a8a8a">DOTFILES: %s AHEAD</span>\n' "${a:-0}"
else
    printf '<span font="Barlow Condensed 12" foreground="#8a8a8a">DOTFILES: TARBALL</span>\n'
fi
