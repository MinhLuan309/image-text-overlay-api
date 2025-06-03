from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import os
import requests
from urllib.parse import urlparse

app = Flask(__name__)
CORS(app)  # Enable CORS for N8N requests

def get_font(size=24, bold=False):
    """Get font with fallback options"""
    font_paths = [
        # Windows fonts
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        # macOS fonts
        "/System/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        # Linux fonts
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    
    if bold:
        bold_fonts = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "/System/Library/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        font_paths = bold_fonts + font_paths
    
    for font_path in font_paths:
        try:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        except:
            continue
    
    # Fallback to default font
    try:
        return ImageFont.load_default()
    except:
        return None

def wrap_text(text, font, max_width):
    """Wrap text to fit within max_width"""
    if not font:
        return [text]
    
    lines = []
    words = text.split(' ')
    current_line = ""
    
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        bbox = font.getbbox(test_line)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
                current_line = word
            else:
                lines.append(word)
    
    if current_line:
        lines.append(current_line)
    
    return lines

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "Image processor API is running"})

@app.route('/add-text-to-image', methods=['POST'])
def add_text_to_image():
    """Add text overlay to image"""
    try:
        # Get image from request
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({"error": "No image file selected"}), 400
        
        # Get parameters
        content = request.form.get('content', '')
        position = request.form.get('position', 'bottom-left')  # top-left, top-right, bottom-left, bottom-right, center
        font_size = int(request.form.get('font_size', 24))
        font_color = request.form.get('font_color', 'white')
        background_color = request.form.get('background_color', 'rgba(0,0,0,0.7)')
        padding = int(request.form.get('padding', 20))
        line_spacing = int(request.form.get('line_spacing', 8))
        
        # Open and process image
        image = Image.open(image_file.stream)
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Create drawing context
        draw = ImageDraw.Draw(image)
        
        # Get font
        font = get_font(font_size)
        
        # Split content into lines (handle \n and <br>)
        content = content.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
        text_lines = content.split('\n')
        
        # Wrap long lines
        img_width, img_height = image.size
        max_text_width = img_width - (padding * 4)  # Leave space for padding
        
        wrapped_lines = []
        for line in text_lines:
            if line.strip():  # Skip empty lines
                wrapped = wrap_text(line.strip(), font, max_text_width)
                wrapped_lines.extend(wrapped)
            else:
                wrapped_lines.append("")  # Keep empty lines for spacing
        
        if not wrapped_lines:
            return jsonify({"error": "No content to add"}), 400
        
        # Calculate text dimensions
        line_heights = []
        max_line_width = 0
        
        for line in wrapped_lines:
            if line and font:
                bbox = font.getbbox(line)
                line_height = bbox[3] - bbox[1]
                line_width = bbox[2] - bbox[0]
                line_heights.append(line_height)
                max_line_width = max(max_line_width, line_width)
            else:
                line_heights.append(font_size if font else 20)  # Default height for empty lines
        
        total_text_height = sum(line_heights) + (line_spacing * (len(wrapped_lines) - 1))
        
        # Calculate position
        background_padding = padding // 2
        bg_width = max_line_width + (background_padding * 2)
        bg_height = total_text_height + (background_padding * 2)
        
        if position == 'bottom-left':
            x = padding
            y = img_height - bg_height - padding
        elif position == 'bottom-right':
            x = img_width - bg_width - padding
            y = img_height - bg_height - padding
        elif position == 'top-left':
            x = padding
            y = padding
        elif position == 'top-right':
            x = img_width - bg_width - padding
            y = padding
        elif position == 'center':
            x = (img_width - bg_width) // 2
            y = (img_height - bg_height) // 2
        else:
            x = padding
            y = img_height - bg_height - padding
        
        # Parse background color
        if background_color.startswith('rgba'):
            # Parse rgba(r,g,b,a)
            rgba_values = background_color.replace('rgba(', '').replace(')', '').split(',')
            r, g, b = map(int, rgba_values[:3])
            a = int(float(rgba_values[3]) * 255)
            bg_color = (r, g, b, a)
        else:
            # Simple color names or hex
            bg_color = (0, 0, 0, 180)  # Default semi-transparent black
        
        # Create overlay for background
        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Draw background rectangle
        overlay_draw.rectangle(
            [x, y, x + bg_width, y + bg_height],
            fill=bg_color
        )
        
        # Composite overlay onto image
        image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(image)
        
        # Draw text lines
        current_y = y + background_padding
        for i, line in enumerate(wrapped_lines):
            if line:  # Skip empty lines
                text_x = x + background_padding
                draw.text((text_x, current_y), line, font=font, fill=font_color)
            current_y += line_heights[i] + line_spacing
        
        # Save processed image to memory
        img_io = io.BytesIO()
        image.save(img_io, 'JPEG', quality=95, optimize=True)
        img_io.seek(0)
        
        return send_file(
            img_io,
            mimetype='image/jpeg',
            as_attachment=False,
            download_name='processed_image.jpg'
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to verify API is working"""
    return jsonify({
        "message": "Image processor API is working!",
        "endpoints": {
            "POST /add-text-to-image": "Add text overlay to image",
            "GET /health": "Health check",
            "GET /test": "Test endpoint"
        },
        "parameters": {
            "image": "Image file (required)",
            "content": "Text content to add",
            "position": "top-left, top-right, bottom-left, bottom-right, center",
            "font_size": "Font size (default: 24)",
            "font_color": "Font color (default: white)",
            "background_color": "Background color (default: rgba(0,0,0,0.7))",
            "padding": "Padding around text (default: 20)",
            "line_spacing": "Space between lines (default: 8)"
        }
    })

if __name__ == '__main__':
    print("🚀 Starting Image Processor API...")
    print("📍 API will be available at: http://localhost:5000")
    print("🔍 Test endpoint: http://localhost:5000/test")
    print("❤️  Health check: http://localhost:5000/health")
    print("🖼️  Main endpoint: POST http://localhost:5000/add-text-to-image")
    app.run(host='0.0.0.0', port=5000, debug=True)