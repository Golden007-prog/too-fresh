# vhs 0.12 + ffmpeg 9 cannot encode gifs here, so render frames and stitch them:
# ffmpeg -framerate 50 -i /tmp/tf-frames/frame-text-%05d.png -framerate 50 -i /tmp/tf-frames/frame-cursor-%05d.png -filter_complex "[0][1]overlay,fps=15,split[a][b];[a]palettegen=max_colors=64[p];[b][p]paletteuse=dither=none" demo/demo.gif
Output "/tmp/tf-frames/"
Set FontSize 16
Set Width 1200
Set Height 520
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 45ms
Hide
Type "export PATH=$PWD/.venv/bin:$PATH PS1='$ ' && cd demo/my-app && clear"
Enter
Show
Type "ls package-lock.json api/"
Enter
Sleep 1s
Type "too-fresh"
Enter
Sleep 4s
Type "too-fresh --ignore openai --days 2"
Enter
Sleep 8s
