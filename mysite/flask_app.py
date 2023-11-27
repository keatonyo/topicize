from flask import Flask, render_template, request
app = Flask(__name__)

import os
import re
import base64
import textract
from pdf2image import convert_from_path
from io import BytesIO
from wordcloud import WordCloud
from collections import Counter

@app.route('/', methods=['GET'])
def home():
    payload = {
        'table': None,
        'total_keywords': None,
        'keywordcloud': None,
        'wordcloud': None,
        'error': None
    }
    return render_template('index.html', payload=payload)

@app.route('/topicize', methods=['POST'])
def topicize():
    # get & save document
    document = request.files['document']
    docname = document.filename
    document.save(docname)
    # try extract document
    try:
        texts = textract.process(docname)
        texts = texts.decode('utf-8')
        texts = texts.replace('\n', ' ').replace('  ', ' ')
    except:
        try:
            # Convert PDF to images
            pages = convert_from_path(docname, 500)
            text_data = ''
            for page in pages:
                text = textract.process(page)
                text = text.decode('utf-8')
                text = text.replace('  ', ' ')
                text_data += text + ' '
            texts = text_data
        except:
            payload = {
                'error': 'Uploaded file is corrupted or uses incompatible encoding (must be UTF-8).',
                'table': None
            }
            os.remove(docname)
            return render_template('index.html', payload=payload)
    # extract keywords from keywords
    keywords = request.form.get('keywords')
    if not keywords or not keywords.strip():
        payload = {
            'error': 'No valid keyword provided. Make sure to separate each keyword with a comma. Whitespaces are ignored.',
            'table': None
        }
        return render_template('index.html', payload=payload)
    else:
        keywords = [re.sub(r'\W+', '', keyword.strip()) for keyword in keywords.split(',') if re.sub(r'\W+', '', keyword.strip())]
        regex = '|'.join(keywords)

    # match keywords to instances in texts
    matches = re.findall(regex, texts, flags=re.IGNORECASE)
    counts = Counter(matches)  # Using Counter to count occurrences of each keyword
    table = [(i+1, keyword, count) for i, (keyword, count) in enumerate(counts.items()) if count > 0]  # Only include keywords with count > 0
    total_keywords = sum(counts.values())

    # create a dictionary of word frequencies from the pairs data
    keyword_freq = {keyword: count for keyword, count in counts.items() if count > 0}  # Only include keywords with count > 0

    # if no keywords found
    if not keyword_freq:
        error_list = 'Uploaded file contains none of the keywords provided. You CAN STILL view Word Cloud to discover insights.'
        keywordcloud_str = None
    else:
        error_list = None
        keywordcloud = WordCloud(width=1600, height=900, background_color='white').generate_from_frequencies(keyword_freq)
        img_buffer = BytesIO()
        keywordcloud.to_image().save(img_buffer, format='PNG')
        keywordcloud_str = base64.b64encode(img_buffer.getvalue()).decode('utf-8')

    # create a WordCloud object and generate the word cloud
    wordcloud = WordCloud(width=1600, height=900, background_color='white').generate(texts)
    # convert the word cloud image to a base64 string
    img_buffer2 = BytesIO()
    wordcloud.to_image().save(img_buffer2, format='PNG')
    wordcloud_str = base64.b64encode(img_buffer2.getvalue()).decode('utf-8')

    # create the payload dictionary with the word cloud image and other data
    payload = {
        'table': table,
        'total_keywords': total_keywords,
        'keywordcloud': keywordcloud_str,
        'wordcloud': wordcloud_str,
        'error': error_list
    }
    # remove uploaded file
    os.remove(docname)
    return render_template('index.html', payload=payload)