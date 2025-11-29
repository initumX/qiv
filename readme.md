# Qt Image Viewer

Handy image viewer and editor built with PySide6. 
The latest version supports also  windows (tested on windows 10, but should also work on windows 11)

![Qt Image Viewer Main Window](./screenshots/01.png)
![Qt Image Viewer Thumbnail Dialog](./screenshots/02.png)


## Features

- **View photo/screenshots**: JPG/JPEG, WebP, PNG
- **Basic editing**: Rotate, flip, crop, copy/paste, resize 
- **White balance tool**: adjusting white balance by grey area of pic
- **Loupe tool**: shows area under cursor on its original size (256x256px by default)
- **Quality-controlled saving**: Save JPEGs with adjustable quality (default: 95), no unintended compression
- **Navigation**: Zoom in/out, fit to window, display at original size, and pan with arrow keys or middle mouse button
- **File browsing**: Navigate forward/backward through images in the same folder
- **EXIF metadata**: View image metadata in a dedicated panel
- **Thumbnails/Open Folder**: Dialog window with thumbnails (uses caching and threads)

## Hotkeys

### Navigation & View
| Action                        | Hotkey(s)                     |
|------------------------------|-------------------------------|
| Next / Previous image        | ← → ↑ ↓ or Mouse wheel        |
| Zoom In / Out                | `Ctrl + Wheel` or `+` / `-`   |
| Original size                | `=` or Double-click           |
| Fit to window                | `W` or Right-click            |
| Pan (move image)             | `Ctrl + Arrows` or Middle drag|

### Editing
| Action                      | Hotkey(s)                     |
|-----------------------------|-------------------------------|
| Enter Crop/Selection mode   | `Ctrl+X`                      |
| Apply Crop                  | `Enter`                       |
| Copy selection / full image | `Ctrl+C`                      |
| Paste image                 | `Ctrl+V`                      |
| White Balance               | `B`                           |
| Resize image                | `Ctrl+R`                      |

### Transform
| Action                        | Hotkey(s)                     |
|------------------------------|-------------------------------|
| Rotate 90° CW / CCW          | `R` / `Shift+R`               |
| Flip Horizontal / Vertical   | `F` / `Shift+F`               |

### File & Info
| Action                        | Hotkey(s)                     |
|------------------------------|-------------------------------|
| Open file                    | `Ctrl+O`                      |
| Open folder / thumbnails     | `Ctrl+T`                      |
| Reload image                 | `F5`                          |
| Move to trash                | `Delete`                      |
| Show EXIF                    | `I`                           |
| About / Help                 | `F1`                          |

### Cancel
| Action                        | Hotkey(s)                     |
|------------------------------|-------------------------------|
| Exit any tool (crop, WB...)  | `Esc` or Right-click          |

## Development & Deployment

- Built with **PySide6** (Qt6)
- Targeted for Linux; deployed as AppImage

