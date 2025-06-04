from flask import Flask, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import os
import textwrap
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def get_font(size, bold=False):
    """Lấy font với size và style phù hợp"""
    font_paths = [
        # Windows
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        # Mac
        "/System/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Arial Bold.ttf",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]
    
    for font_path in font_paths:
        try:
            if bold and "bold" in font_path.lower():
                return ImageFont.truetype(font_path, size)
            elif not bold and "bold" not in font_path.lower():
                return ImageFont.truetype(font_path, size)
        except:
            continue
    
    # Fallback to default font
    return ImageFont.load_default()

def wrap_text(text, font, max_width):
    """Chia text thành nhiều dòng theo chiều rộng tối đa"""
    lines = []
    
    # Tách text theo dấu xuống dòng có sẵn
    paragraphs = text.split('\n')
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            lines.append('')
            continue
            
        # Ước tính số ký tự trên một dòng
        avg_char_width = font.getbbox('A')[2] - font.getbbox('A')[0]
        chars_per_line = max(1, max_width // avg_char_width)
        
        # Wrap text
        wrapped_lines = textwrap.wrap(paragraph, width=chars_per_line)
        if not wrapped_lines:
            wrapped_lines = [paragraph]
            
        lines.extend(wrapped_lines)
    
    return lines

@app.route('/add-text-to-image', methods=['POST'])
def add_text_to_image():
    try:
        # Nhận dữ liệu từ request
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
            
        image_file = request.files['image']
        content = request.form.get('content', '').strip()
        username = request.form.get('username', '@ngdp.9')
        
        if not content:
            return jsonify({'error': 'No content provided'}), 400
        
        # Đọc và mở ảnh
        image_data = image_file.read()
        image = Image.open(io.BytesIO(image_data)).convert('RGBA')
        
        # Lấy kích thước ảnh
        img_width, img_height = image.size
        
        # Tạo layer overlay để vẽ text
        overlay = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Cấu hình font
        content_font = get_font(32, bold=False)  # Font cho nội dung chính
        username_font = get_font(24, bold=True)   # Font cho username
        
        # Cấu hình vị trí và kích thước
        margin = 40
        content_area_width = img_width // 2 - margin * 2  # Nửa ảnh cho content
        content_x = margin
        
        # Xử lý và chia content thành các dòng
        content_lines = wrap_text(content, content_font, content_area_width)
        
        # Tính toán chiều cao cần thiết cho text
        line_height = content_font.getbbox('Ay')[3] - content_font.getbbox('Ay')[1] + 8
        total_content_height = len(content_lines) * line_height
        
        # Vị trí bắt đầu vẽ content (căn giữa theo chiều dọc, bên trái)
        content_start_y = (img_height - total_content_height) // 2
        
        # Tạo background mờ cho text content
        padding = 20
        bg_width = content_area_width + padding * 2
        bg_height = total_content_height + padding * 2
        bg_x = content_x - padding
        bg_y = content_start_y - padding
        
        # Vẽ background với độ trong suốt
        background_overlay = Image.new('RGBA', (bg_width, bg_height), (0, 0, 0, 120))
        
        # Làm mờ background một chút
        background_overlay = background_overlay.filter(ImageFilter.GaussianBlur(radius=1))
        
        # Paste background lên overlay
        overlay.paste(background_overlay, (bg_x, bg_y), background_overlay)
        
        # Vẽ content text
        current_y = content_start_y
        for line in content_lines:
            if line.strip():  # Chỉ vẽ dòng có nội dung
                draw.text((content_x, current_y), line, font=content_font, fill='white')
            current_y += line_height
        
        # Vẽ username ở góc phải dưới
        username_bbox = draw.textbbox((0, 0), username, font=username_font)
        username_width = username_bbox[2] - username_bbox[0]
        username_height = username_bbox[3] - username_bbox[1]
        
        username_x = img_width - username_width - margin
        username_y = img_height - username_height - margin
        
        # Background cho username
        username_bg_padding = 10
        username_bg = Image.new('RGBA', 
                               (username_width + username_bg_padding * 2, 
                                username_height + username_bg_padding * 2), 
                               (0, 0, 0, 100))
        
        overlay.paste(username_bg, 
                     (username_x - username_bg_padding, 
                      username_y - username_bg_padding), 
                     username_bg)
        
        # Vẽ username
        draw.text((username_x, username_y), username, font=username_font, fill='white')
        
        # Kết hợp overlay với ảnh gốc
        final_image = Image.alpha_composite(image, overlay)
        
        # Convert về RGB để save JPEG
        final_image = final_image.convert('RGB')
        
        # Lưu vào BytesIO
        img_io = io.BytesIO()
        final_image.save(img_io, 'JPEG', quality=95, optimize=True)
        img_io.seek(0)
        
        return send_file(
            img_io, 
            mimetype='image/jpeg',
            as_attachment=False,
            download_name='processed_image.jpg'
        )
        
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return jsonify({'error': f'Image processing failed: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Image processing API is running'})

if __name__ == '__main__':
    print("🚀 Starting Image Text Overlay API...")
    print("📍 API will be available at: http://localhost:5000")
    print("🔗 Health check: http://localhost:5000/health")
    print("📝 Main endpoint: POST http://localhost:5000/add-text-to-image")
    
    app.run(host='0.0.0.0', port=5000, debug=True)