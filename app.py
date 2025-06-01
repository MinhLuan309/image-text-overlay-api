from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import os

app = Flask(__name__)
CORS(app)

def add_text_to_image(image_data, text, font_size=36, font_color="#FFFFFF", 
                     bg_opacity=0.8, position="bottom"):
    """
    Thêm text vào ảnh với background semi-transparent
    """
    try:
        # Mở ảnh từ binary data
        image = Image.open(io.BytesIO(image_data))
        
        # Convert sang RGBA nếu cần
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Tạo overlay layer để vẽ text
        overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Load font (fallback nếu không có)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
        
        # Tính toán kích thước text
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Tính toán vị trí
        img_width, img_height = image.size
        
        if position == "top":
            text_x = (img_width - text_width) // 2
            text_y = 50
            bg_y = 20
        elif position == "center":
            text_x = (img_width - text_width) // 2
            text_y = (img_height - text_height) // 2
            bg_y = text_y - 20
        else:  # bottom
            text_x = (img_width - text_width) // 2
            text_y = img_height - text_height - 50
            bg_y = text_y - 20
        
        # Vẽ background cho text
        bg_color = (0, 0, 0, int(255 * bg_opacity))
        padding = 20
        draw.rectangle([
            text_x - padding, bg_y,
            text_x + text_width + padding, text_y + text_height + 20
        ], fill=bg_color)
        
        # Vẽ text
        draw.text((text_x, text_y), text, font=font, fill=font_color)
        
        # Kết hợp overlay với ảnh gốc
        result = Image.alpha_composite(image, overlay)
        
        # Convert về RGB để save as JPEG
        if result.mode == 'RGBA':
            background = Image.new('RGB', result.size, (255, 255, 255))
            background.paste(result, mask=result.split()[-1])
            result = background
        
        return result
        
    except Exception as e:
        raise Exception(f"Error processing image: {str(e)}")

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Image Text Overlay API",
        "version": "1.0.0"
    })

@app.route('/add-text-to-image', methods=['POST'])
def add_text_endpoint():
    """
    API endpoint để thêm text vào ảnh
    """
    try:
        # Kiểm tra có file ảnh không
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No image file selected"}), 400
        
        # Đọc parameters
        content = request.form.get('content', 'Sample Text')
        font_size = int(request.form.get('font_size', 36))
        font_color = request.form.get('font_color', '#FFFFFF')
        bg_opacity = float(request.form.get('bg_opacity', 0.8))
        position = request.form.get('position', 'bottom')
        
        # Đọc image data
        image_data = file.read()
        
        # Xử lý ảnh
        result_image = add_text_to_image(
            image_data=image_data,
            text=content,
            font_size=font_size,
            font_color=font_color,
            bg_opacity=bg_opacity,
            position=position
        )
        
        # Save ảnh kết quả vào memory
        img_io = io.BytesIO()
        result_image.save(img_io, 'JPEG', quality=95)
        img_io.seek(0)
        
        return send_file(
            img_io,
            mimetype='image/jpeg',
            as_attachment=True,
            download_name='processed_image.jpg'
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)