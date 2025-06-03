from flask import Flask, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont
import io
import os
import logging
from datetime import datetime
import traceback

app = Flask(__name__)

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageTextProcessor:
    def __init__(self):
        self.default_font_size = 24
        self.line_spacing = 8
        self.margin_left = 30
        self.margin_bottom = 40
        self.background_alpha = 120  # Độ trong suốt background
        
    def get_font(self, size=24):
        """Lấy font phù hợp, ưu tiên font Vietnamese"""
        font_paths = [
            # Windows fonts
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "C:/Windows/Fonts/tahoma.ttf",
            # Ubuntu/Linux fonts
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            # macOS fonts
            "/System/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
        
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, size)
            except Exception as e:
                logger.warning(f"Cannot load font {font_path}: {e}")
                continue
        
        # Fallback to default font
        try:
            return ImageFont.load_default()
        except:
            return None

    def calculate_text_dimensions(self, text_lines, font):
        """Tính toán kích thước text block"""
        if not font:
            return 0, 0
            
        max_width = 0
        total_height = 0
        
        for line in text_lines:
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1]
            
            max_width = max(max_width, line_width)
            total_height += line_height + self.line_spacing
        
        # Trừ bớt line_spacing cuối cùng
        total_height -= self.line_spacing if text_lines else 0
        
        return max_width, total_height

    def create_text_overlay(self, image, content):
        """Tạo text overlay lên ảnh"""
        try:
            # Chuyển đổi ảnh sang RGBA để hỗ trợ transparency
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            img_width, img_height = image.size
            
            # Tách nội dung thành các dòng
            text_lines = content.split('<br>') if '<br>' in content else content.split('\n')
            text_lines = [line.strip() for line in text_lines if line.strip()]
            
            if not text_lines:
                return image
            
            # Tính toán font size dựa trên kích thước ảnh
            base_font_size = max(18, min(32, img_width // 25))
            font = self.get_font(base_font_size)
            
            if not font:
                logger.error("Cannot load any font")
                return image
            
            # Tính toán kích thước text block
            text_width, text_height = self.calculate_text_dimensions(text_lines, font)
            
            # Tính toán vị trí text (bottom-left với margin)
            text_x = self.margin_left
            text_y = img_height - self.margin_bottom - text_height
            
            # Tạo overlay với background trong suốt
            overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            
            # Vẽ background cho text (rounded rectangle)
            padding = 15
            bg_x1 = text_x - padding
            bg_y1 = text_y - padding
            bg_x2 = text_x + text_width + padding
            bg_y2 = text_y + text_height + padding
            
            # Vẽ background với góc bo tròn
            overlay_draw.rounded_rectangle(
                [(bg_x1, bg_y1), (bg_x2, bg_y2)],
                radius=8,
                fill=(0, 0, 0, self.background_alpha)
            )
            
            # Vẽ text lên overlay
            current_y = text_y
            for line in text_lines:
                overlay_draw.text(
                    (text_x, current_y),
                    line,
                    font=font,
                    fill=(255, 255, 255, 255)  # Màu trắng
                )
                
                # Tính chiều cao dòng hiện tại
                bbox = font.getbbox(line)
                line_height = bbox[3] - bbox[1]
                current_y += line_height + self.line_spacing
            
            # Kết hợp overlay với ảnh gốc
            result = Image.alpha_composite(image, overlay)
            
            # Chuyển về RGB để lưu JPEG
            if result.mode == 'RGBA':
                rgb_image = Image.new('RGB', result.size, (255, 255, 255))
                rgb_image.paste(result, mask=result.split()[-1])
                result = rgb_image
            
            return result
            
        except Exception as e:
            logger.error(f"Error in create_text_overlay: {str(e)}")
            logger.error(traceback.format_exc())
            return image

processor = ImageTextProcessor()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Image Text Overlay Service'
    })

@app.route('/add-text-to-image', methods=['POST'])
def add_text_to_image():
    """Main endpoint để xử lý ảnh"""
    try:
        logger.info("Received request for image processing")
        
        # Kiểm tra request
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({'error': 'Empty image file'}), 400
        
        # Lấy parameters
        content = request.form.get('content', '').strip()
        if not content:
            return jsonify({'error': 'No content provided'}), 400
        
        logger.info(f"Processing image: {image_file.filename}")
        logger.info(f"Content: {content}")
        
        # Đọc và xử lý ảnh
        image_data = image_file.read()
        
        try:
            image = Image.open(io.BytesIO(image_data))
        except Exception as e:
            logger.error(f"Cannot open image: {str(e)}")
            return jsonify({'error': 'Invalid image file'}), 400
        
        logger.info(f"Image size: {image.size}, mode: {image.mode}")
        
        # Xử lý text overlay
        processed_image = processor.create_text_overlay(image, content)
        
        # Lưu ảnh đã xử lý vào memory
        img_io = io.BytesIO()
        processed_image.save(img_io, 'JPEG', quality=95, optimize=True)
        img_io.seek(0)
        
        logger.info("Image processed successfully")
        
        return send_file(
            img_io,
            mimetype='image/jpeg',
            as_attachment=False,
            download_name=f"processed_{image_file.filename}"
        )
        
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint để kiểm tra service"""
    return jsonify({
        'message': 'Image Text Overlay Service is running',
        'endpoints': {
            'health': '/health',
            'process': '/add-text-to-image (POST)',
            'test': '/test'
        },
        'usage': {
            'method': 'POST',
            'content_type': 'multipart/form-data',
            'parameters': {
                'image': 'Image file (required)',
                'content': 'Text content with <br> for line breaks (required)'
            }
        }
    })

if __name__ == '__main__':
    print("🚀 Starting Image Text Overlay Service...")
    print("📋 Available endpoints:")
    print("   - GET  /health - Health check")
    print("   - GET  /test - Service info")
    print("   - POST /add-text-to-image - Process image")
    print("🌐 Server running on http://0.0.0.0:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
