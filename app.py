
from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
import emoji
import re
import os

app = Flask(__name__)

# Ensure the uploads folder exists
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Function to clean the WhatsApp chat data and convert it to a DataFrame
def whatsapp_data_to_dataframe(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    pattern = r"^(\d{1,2}/\d{1,2}/\d{2,4}), (\d{1,2}:\d{2}) - ([^:]+): (.*)"
    dates, times, users, messages = [], [], [], []

    for line in lines:
        match = re.match(pattern, line)
        if match:
            date, time, user, message = match.groups()
            dates.append(date)
            times.append(time)
            users.append(user)
            messages.append(message)

    df = pd.DataFrame({'Date': dates, 'Time': times, 'User': users, 'Message': messages})
    return df

# Function to extract emojis from text
def extract_emojis(text):
    return ''.join(c for c in text if c in emoji.EMOJI_DATA)

# Function to clean text (remove special characters and emojis)
def clean_text(text):
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    text = re.sub(r'\d+', '', text)  # Remove digits
    text = ''.join(c for c in text if not c in emoji.EMOJI_DATA)  # Remove emojis
    return text.lower()

# Function to analyze a specific user's activity
def analyze_users_activity(df):
    # Number of messages per user
    num_messages_per_user = df['User'].value_counts()
    # Count media shared by each user
    media_shared_per_user = df[df['Message'] == '<Media omitted>']['User'].value_counts()
    
    # Extract emojis and count their usage
    df['Emojis'] = df['Message'].apply(extract_emojis)
    # Convert emoji data to Counter
    emoji_counts_per_user = df.groupby('User')['Emojis'].apply(lambda x: Counter(''.join(x)))
    # Clean the messages to prepare for word frequency count
    df['Cleaned Message'] = df['Message'].apply(clean_text)
    # Convert word data to Counter
    word_counts_per_user = df.groupby('User')['Cleaned Message'].apply(lambda x: Counter(' '.join(x).split()))
    
    # Prepare the results for each user
    user_activity = {}
    for user in df['User'].unique():
        # Retrieve Counter objects for emojis and words
        emoji_counter = emoji_counts_per_user.get(user, Counter())
        word_counter = word_counts_per_user.get(user, Counter())

        # Convert Counter to a list of tuples and sort it
        emoji_counts = dict(emoji_counter)
        most_common_emojis = sorted(emoji_counts.items(), key=lambda item: item[1], reverse=True)[:5]

        word_counts = dict(word_counter)
        most_common_words = sorted(word_counts.items(), key=lambda item: item[1], reverse=True)[:5]

        user_activity[user] = {
            'num_messages': num_messages_per_user.get(user, 0),
            'media_shared': media_shared_per_user.get(user, 0),
            'emoji_counts': most_common_emojis,
            'most_common_words': most_common_words
        }

    return user_activity


def analyze_overall_activity(df):
    total_messages = df.shape[0]
    total_emojis = sum(df['Message'].apply(lambda x: len(extract_emojis(x))))

    # Most active users
    active_users = df['User'].value_counts()

    # Most frequently used emojis
    all_emojis = ''.join(df['Message'].apply(extract_emojis))
    emoji_counter = Counter(all_emojis)
    most_common_emojis = emoji_counter.most_common(5)

    return {
        'total_messages': total_messages,
        'total_emojis': total_emojis,
        'active_users': active_users.to_dict(),
        'most_common_emojis': most_common_emojis
    }

def analyze_user_activity(df, user):
    user_df = df[df['User'] == user]
    if user_df.empty:
        return None

    num_messages = user_df.shape[0]
    media_shared = user_df[user_df['Message'] == '<Media omitted>'].shape[0]
    all_emojis = ''.join(user_df['Message'].apply(extract_emojis))
    emoji_counter = Counter(all_emojis).most_common(5)
    cleaned_messages = ' '.join(user_df['Message'].apply(clean_text))
    word_counter = Counter(cleaned_messages.split()).most_common(5)

    return {
        'num_messages': num_messages,
        'media_shared': media_shared,
        'emoji_counts': emoji_counter,
        'most_common_words': word_counter
    }


# Route to upload file and analyze user
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']

        if not file or not file.filename.endswith('.txt'):
            return "Invalid file format. Please upload a .txt file.", 400
        # Save the uploaded file
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        try:
            # Clean and convert the WhatsApp data
            whatsapp_df = whatsapp_data_to_dataframe(file_path)
            # Perform analysis
            # user_activity = analyze_user_activity(whatsapp_df)
            overall_activity = analyze_overall_activity(whatsapp_df)

            # Render the results
            return render_template('result.html', overall_activity=overall_activity)
        except Exception as e:
            return f"An error occurred: {e}", 500

    return render_template('index.html')

@app.route('/user_analysis', methods=['POST'])
def user_analysis():
    user = request.form.get('username')
    file_path = os.path.join(UPLOAD_FOLDER, request.form.get('file_name'))
    
    try:
        whatsapp_df = whatsapp_data_to_dataframe(file_path)
        user_activity = analyze_user_activity(whatsapp_df, user)
        if user_activity:
            return render_template('user_result.html', user=user, user_activity=user_activity)
        else:
            return f"No data found for user: {user}", 404
    except Exception as e:
        return f"An error occurred: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)
