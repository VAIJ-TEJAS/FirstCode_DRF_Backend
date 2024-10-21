from PIL import Image, ImageDraw, ImageFont


def fontsize(username):
    max_output = 180
    min_output = 92

    username_length = len(username)
    max_length = 40
    min_length = 4

    # Calculate the proportionate number using inverse relationship
    if username_length < min_length:
        username_length = min_length
    elif username_length > max_length:
        username_length = max_length

    proportionate_number = max_output - ((username_length - min_length) / (max_length - min_length)) * (max_output - min_output)
    return round(proportionate_number)


def generate_certificate(student_name, course_name, issue_date, output_path, template_path='cert_template.png', font_path='Keraleeyam-Regular.ttf'):
    # Load the base certificate image
    base_image = Image.open(template_path)
    draw = ImageDraw.Draw(base_image)

    # Define the font and size
    name_f = fontsize(student_name)
    name_font = ImageFont.truetype(font_path, name_f)
    course_f = fontsize(course_name)
    course_font = ImageFont.truetype(font_path, 120)
    date_font = ImageFont.truetype(font_path, 80)

    # Define text positions
    name_position = (1500, 900)
    course_position = (1500, 1260)
    date_position = (1620, 1382)

    # Calculate the bounding box of the text (left, top, right, bottom)
    name_bbox = draw.textbbox(name_position, student_name, font=name_font)
    course_bbox = draw.textbbox(course_position, course_name, font=course_font)
    date_bbox = draw.textbbox(date_position, issue_date, font=date_font)

    # Calculate the width and height of the text to be added
    name_width, name_height = name_bbox[2] - name_bbox[0], name_bbox[3] - name_bbox[1]
    course_width, course_height = course_bbox[2] - course_bbox[0], course_bbox[3] - course_bbox[1]
    date_width, date_height = date_bbox[2] - date_bbox[0], date_bbox[3] - date_bbox[1]

    # Adjust the position to center the text
    name_position = (name_position[0] - name_width // 2, name_position[1] - name_height // 2)
    course_position = (course_position[0] - course_width // 2, course_position[1] - course_height // 2)
    date_position = (date_position[0] - date_width // 2, date_position[1] - date_height // 2)

    # Add text to the image
    draw.text(name_position, student_name, font=name_font, fill="black")
    draw.text(course_position, course_name, font=course_font, fill="black")
    draw.text(date_position, issue_date, font=date_font, fill="black")

    # Save the final certificate image
    base_image.save(output_path)

    return output_path


# Example usage
student_name = "Tejas Vaij"
course_name = "Python for Beginners"
issue_date = "01-01-2024"

output_path = "Completed_Certificate.png"
template_path = "cert_template.png"
font_path = "Keraleeyam-Regular.ttf"