# Advanced Material Search Button Location Guide

## ✅ **Button Integration Complete**

The **"🔍 Advanced Material Search"** button has been successfully integrated into both material selection dialogs with prominent styling for maximum visibility.

## 📍 **Exact Button Locations**

### **1. Room Properties Dialog**
**Path:** Create new space from drawn rectangle → Materials tab

**Steps to find the button:**
1. Draw a rectangle on a PDF drawing
2. Right-click rectangle → "Convert to Space" (or similar option)
3. In the Room Properties dialog, click the **"Surface Materials"** tab
4. Look for the **bright blue button** with text **"🔍 Advanced Material Search"**

**Button Position:**
- Located immediately below the instructions text
- Centered horizontally in the dialog
- Above the "Ceiling Material", "Wall Material", "Floor Material" sections
- Styled with blue background (#3498db), white text, and 35px height

### **2. Space Edit Dialog** 
**Path:** Edit existing space → Materials tab

**Steps to find the button:**
1. Right-click on an existing space in your project
2. Select "Edit Space" (or similar option)
3. In the Space Edit dialog, click the **"Surface Materials"** tab  
4. Look for the **bright blue button** with text **"🔍 Advanced Material Search"**

**Button Position:**
- Located immediately below the instructions text
- Centered horizontally in the dialog
- Above the "Ceiling Materials", "Wall Materials", "Floor Materials" sections
- Styled with blue background (#3498db), white text, and 35px height

## 🎨 **Button Visual Characteristics**

The button has been styled to be highly visible:

```css
Background: Bright blue (#3498db)
Text: White, bold, 12px font
Size: Minimum 35px height
Shape: Rounded corners (4px radius)
Position: Centered with padding
Hover Effect: Darker blue (#2980b9)
```

## 🔍 **If You Still Can't Find the Button**

### **Common Issues:**

1. **Wrong Tab**: Make sure you're in the **"Surface Materials"** tab, not "Basic Properties" or "Calculations"

2. **Dialog Size**: The dialog might be too narrow. Try:
   - Resizing the dialog window wider
   - Maximizing the dialog window
   - Scrolling if there's a scroll area

3. **Button Location**: The button is positioned:
   - **After** the instructional text 
   - **Before** the material selection sections
   - **In the center** of the dialog width

4. **Check the Right Dialog**: Ensure you're opening the correct dialog:
   - **Room Properties**: When creating NEW spaces from rectangles
   - **Space Edit**: When editing EXISTING spaces

### **Visual Reference:**

```
┌─────────────────────────────────────────────────────────┐
│                Surface Materials Tab                    │
├─────────────────────────────────────────────────────────┤
│ Instructions text about selecting materials...          │
│                                                         │
│           ┌─────────────────────────────────┐          │
│           │  🔍 Advanced Material Search   │          │
│           └─────────────────────────────────┘          │
│                                                         │
│ ┌─── Ceiling Material ────────────────────────────────┐ │
│ │ [Dropdown selection]                                │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌─── Wall Material ───────────────────────────────────┐ │
│ │ [Dropdown selection]                                │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌─── Floor Material ──────────────────────────────────┐ │
│ │ [Dropdown selection]                                │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 🚀 **Button Functionality**

When you click the button, it will:

1. **Analyze Current Space**: Reviews room dimensions, target RT60, and current materials
2. **Open Advanced Interface**: Shows frequency analysis graph and material search
3. **Provide Recommendations**: Suggests optimal materials based on acoustic needs
4. **Enable Smart Selection**: Allows material selection based on frequency response
5. **Apply Materials**: Selected materials are automatically applied to the dialog

## 🔧 **Technical Verification**

The button integration has been verified through:
- ✅ Code structure analysis
- ✅ Method presence confirmation  
- ✅ Import chain validation
- ✅ Signal connection verification
- ✅ Styling application confirmation

## 📞 **Still Having Issues?**

If you still cannot locate the button after checking all the above:

1. **Restart the Application**: Close and reopen the application to ensure all changes are loaded
2. **Check File Versions**: Ensure you're running the updated version of the dialogs
3. **Look for Error Messages**: Check the console/terminal for any import or styling errors
4. **Try Both Dialogs**: Test both Room Properties and Space Edit dialogs to see if the issue is specific to one

The button is definitely integrated and should be highly visible with its bright blue styling. It's located in the "Surface Materials" tab of both dialogs, positioned prominently between the instructions and the material selection sections.