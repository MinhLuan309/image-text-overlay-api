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
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(base_dir, 'fonts', 'arial.ttf' if not bold else 'arialbd.ttf')
    try:
        return ImageFont.truetype(font_path, size)
    except:
        print(f"Font not found at {font_path}, using default font")
        return ImageFont.load_default()

def wrap_text(text, font, max_width):
    """Chia text thành nhiều dòng theo chiều rộng tối đa"""
    lines = []
    paragraphs = text.split('\n')
    for paragraph in paragraphs:
        if not paragraph.strip():
            lines.append('')
            continue
        avg_char_width = font.getbbox('A')[2] - font.getbbox('A')[0]
        chars_per_line = max(1, max_width // avg_char_width)
        wrapped_lines = textwrap.wrap(paragraph, width=chars_per_line)
        if not wrapped_lines:
            wrapped_lines = [paragraph]
        lines.extend(wrapped_lines)
    return lines

@app.route('/add-text-to-image', methods=['POST'])
def add_text_to_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        image_file = request.files['image']
        content = request.form.get('content', '').strip()
        username = request.form.get('username', '@ngdp.9')
        if not content:
            return jsonify({'error': 'No content provided'}), 400
        image_data = image_file.read()
        image = Image.open(io.BytesIO(image_data)).convert('RGBA')
        img_width, img_height = image.size
        overlay = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        content_font = get_font(32, bold=False)
        username_font = get_font(24, bold=True)
        margin = 40
        content_area_width = img_width // 2 - margin * 2
        content_x = margin
        content_lines = wrap_text(content, content_font, content_area_width)
        line_height = content_font.getbbox('Ay')[3] - content_font.getbbox('Ay')[1] + 8
        total_content_height = len(content_lines) * line_height
        content_start_y = (img_height - total_content_height) // 2
        padding = 20
        bg_width = content_area_width + padding * 2
        bg_height = total_content_height + padding * 2
        bg_x = content_x - padding
        bg_y = content_start_y - padding
        background_overlay = Image.new('RGBA', (bg_width, bg_height), (0, 0, 0, 120))
        background_overlay = background_overlay.filter(ImageFilter.GaussianBlur(radius=1))
        overlay.paste(background_overlay, (bg_x, bg_y), background_overlay)
        current_y = content_start_y
        for line in content_lines:
            if line.strip():
                draw.text((content_x, current_y), line, font=content_font, fill='white')
            current_y += line_height
        username_bbox = draw.textbbox((0, 0), username, font=username_font)
        username_width = username_bbox[2] - username_bbox[0]
        username_height = username_bbox[3] - username_bbox[1]
        username_x = img_width - username_width - margin
        username_y = img_height - username_height - margin
        username_bg_padding = 10
        username_bg = Image.new('RGBA', (username_width + username_bg_padding * 2, username_height + username_bg_padding * 2), (0, 0, 0, 100))
        overlay.paste(username_bg, (username_x - username_bg_padding, username_y - username_bg_padding), username_bg)
        draw.text((username_x, username_y), username, font=username_font, fill='white')
        final_image = Image.alpha_composite(image, overlay)
        final_image = final_image.convert('RGB')
        img_io = io.BytesIO()
        final_image.save(img_io, 'JPEG', quality=95, optimize=True)
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg', as_attachment=False, download_name='processed_image.jpg')
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return jsonify({'error': f'Image processing failed: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Image processing API is running'})

# Gunicorn sẽ xử lý khởi động, không cần đoạn này khi deploy trên Railway
# if __name__ == '__main__':
#     port = int(os.environ.get('PORT', 5000))
#     print("🚀 Starting Image Text Overlay API...")
#     print(f"📍 Listening on port: {port}")
#     print("🔗 Health check: /health")
#     print("📝 Main endpoint: POST /add-text-to-image")
#     app.run(host='0.0.0.0', port=port, debug=False)