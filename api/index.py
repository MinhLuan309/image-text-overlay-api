from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import json
import os

app = Flask(__name__)

@app.route('/api/add-text-to-image', methods=['POST'])
def add_text_to_image():
    try:
        # Nhận dữ liệu JSON
        data = request.get_json()
        
        if not data or 'imageData' not in data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing imageData or content'
            }), 400
        
        # Decode base64 image
        image_data = base64.b64decode(data['imageData'])
        content = data['content']
        handle = data.get('handle', '@ngdp.9')  # Default handle
        
        # Mở ảnh
        image = Image.open(io.BytesIO(image_data)).convert('RGB')
        draw = ImageDraw.Draw(image)
        
        # Lấy kích thước ảnh
        img_width, img_height = image.size
        
        # Xử lý text - tách theo <br> hoặc \n
        lines = content.replace('<br>', '\n').replace('<br/>', '\n').split('\n')
        lines = [line.strip() for line in lines if line.strip()]
        
        # Cấu hình font theo tỷ lệ ảnh (giống layout mẫu)
        base_font_size = max(20, img_width // 25)  # Tối thiểu 20px
        
        # Thử load font, fallback nếu không có
        try:
            # Vercel có sẵn DejaVu fonts
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            font = ImageFont.truetype(font_path, base_font_size)
            handle_font = ImageFont.truetype(font_path, int(base_font_size * 0.7))
        except:
            try:
                # Fallback sang font mặc định
                font = ImageFont.load_default()
                handle_font = ImageFont.load_default()
            except:
                # Cuối cùng dùng font cơ bản
                font = ImageFont.load_default()
                handle_font = font
        
        # Vị trí text bắt đầu từ 1/3 chiều cao ảnh (giống mẫu)
        text_start_y = int(img_height * 0.35)
        left_margin = int(img_width * 0.08)  # 8% từ lề trái
        line_spacing = int(base_font_size * 1.6)  # Khoảng cách dòng
        
        # Vẽ từng dòng text
        for index, line in enumerate(lines):
            y = text_start_y + (index * line_spacing)
            
            # Vẽ shadow cho text (để nổi bật trên nền)
            draw.text((left_margin + 2, y + 2), line, font=font, fill=(0, 0, 0, 77))  # Shadow
            
            # Vẽ text chính màu trắng
            draw.text((left_margin, y), line, font=font, fill='white')
        
        # Thêm handle ở góc dưới phải (giống mẫu)
        handle_x = img_width - int(img_width * 0.05)  # 5% từ lề phải
        handle_y = img_height - int(img_height * 0.08)  # 8% từ đáy
        
        # Đo kích thước text handle để align right
        try:
            bbox = draw.textbbox((0, 0), handle, font=handle_font)
            handle_width = bbox[2] - bbox[0]
        except:
            handle_width = len(handle) * int(base_font_size * 0.4)  # Ước lượng
        
        final_handle_x = handle_x - handle_width
        
        # Shadow cho handle
        draw.text((final_handle_x + 1, handle_y + 1), handle, font=handle_font, fill=(0, 0, 0, 102))
        
        # Handle chính
        draw.text((final_handle_x, handle_y), handle, font=handle_font, fill='white')
        
        # Convert về base64
        img_io = io.BytesIO()
        image.save(img_io, 'JPEG', quality=95, optimize=True)
        img_io.seek(0)
        
        result_base64 = base64.b64encode(img_io.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'imageData': result_base64,
            'mimeType': 'image/jpeg',
            'size': len(img_io.getvalue()),
            'originalSize': len(image_data),
            'processedAt': data.get('timestamp', 'unknown')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'N8N Image Text Processor',
        'version': '1.0.0'
    })

# Root endpoint
@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'message': 'N8N Image Text Processor API',
        'endpoints': {
            'process': '/api/add-text-to-image (POST)',
            'health': '/api/health (GET)'
        }
    })

# Vercel handler
def handler(event, context):
    return app(event, context)

if __name__ == '__main__':
    app.run(debug=True)