import matplotlib
matplotlib.use('Agg')

from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
import emoji
import re
import os
from wordcloud import WordCloud


app2 = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

     # Convert 'Date' column to datetime format
    df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%y', errors='coerce')  # Adjust the format as needed
    df['Hour'] = df['Time'].apply(lambda x: pd.to_datetime(x, format='%H:%M').hour)
    
    # Create 'Cleaned Message' column to remove special characters and emojis
    df['Cleaned Message'] = df['Message'].apply(clean_text)
    
    return df

def extract_emojis(text):
    return ''.join(c for c in text if c in emoji.EMOJI_DATA)

def clean_text(text):
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\d+', '', text)
    text = ''.join(c for c in text if not c in emoji.EMOJI_DATA)
    return text.lower()

# Overall analysis function
def overall_analysis(df):
    total_messages = df.shape[0]
    total_emojis = df['Message'].apply(extract_emojis).str.len().sum()

    active_users = df['User'].value_counts().to_dict()
    all_emojis = ''.join(df['Message'].apply(extract_emojis))
    most_common_emojis = Counter(all_emojis).most_common(5)

    return {
        'total_messages': total_messages,
        'total_emojis': total_emojis,
        'active_users': active_users,
        'most_common_emojis': most_common_emojis
    }

# Function to analyze a specific user's activity
def analyze_user_activity(df, user):
    user_df = df[df['User'] == user]

    if user_df.empty:
        return None

    num_messages = user_df.shape[0]
    media_shared = user_df[user_df['Message'] == '<Media omitted>'].shape[0]
    user_df['Emojis'] = user_df['Message'].apply(extract_emojis)
    emoji_counts = Counter(''.join(user_df['Emojis'])).most_common(5)
    user_df['Cleaned Message'] = user_df['Message'].apply(clean_text)
    word_counts = Counter(' '.join(user_df['Cleaned Message']).split()).most_common(5)

    return {
        'num_messages': num_messages,
        'media_shared': media_shared,
        'emoji_counts': emoji_counts,
        'most_common_words': word_counts
    }

# Function to plot and save user activity visualizations
def plot_user_activity(words_per_user, media_per_user, weekly_activity, most_active_user, df):
    # Ensure the 'static' folder exists for storing images
    if not os.path.exists('static'):
        os.makedirs('static')

    # Plot the number of words sent by each user
    plt.figure(figsize=(8, 4))
    words_per_user.plot(kind='bar', color='skyblue')
    plt.title('Words Sent by Each User')
    plt.ylabel('Number of Words')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('static/words_per_user.png')  # Save the plot as an image
    plt.close()

    # Plot the number of media shared by each user
    plt.figure(figsize=(8, 4))
    media_per_user.plot(kind='bar', color='orange')
    plt.title('Media Shared by Each User')
    plt.ylabel('Number of Media')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('static/media_per_user.png')  # Save the plot as an image
    plt.close()

    # Plot weekly activity of each user
    plt.figure(figsize=(8, 4))
    weekly_activity.plot(kind='line', marker='o')
    plt.title('Weekly Activity of Each User')
    plt.ylabel('Number of Messages')
    plt.xlabel('Week Number')
    plt.legend(title='User')
    plt.tight_layout()
    plt.savefig('static/weekly_activity.png')  # Save the plot as an image
    plt.close()

    # Display the most active user in a pie chart
    plt.figure(figsize=(4, 4))
    plt.pie([df['User'].value_counts()[most_active_user], df.shape[0] - df['User'].value_counts()[most_active_user]],
            labels=[most_active_user, 'Others'], autopct='%1.1f%%', colors=['lightcoral', 'lightgrey'])
    plt.title('Most Active User')
    plt.tight_layout()
    plt.savefig('static/most_active_user.png')  # Save the plot as an image
    plt.close()

     # Display each user's activity in a pie chart
    plt.figure(figsize=(4, 4))
    user_message_counts = df['User'].value_counts()
    plt.pie(user_message_counts, labels=user_message_counts.index, autopct='%1.1f%%', colors=plt.cm.Paired(range(len(user_message_counts))))
    plt.title('User Activity Distribution in WhatsApp Group Chat')
    plt.tight_layout()
    plt.savefig('static/user_activity_distribution.png')  # Save the plot as an image
    plt.close()

    all_messages = ' '.join(df['Cleaned Message'])
    text = ' '.join(all_messages)
    wordcloud = WordCloud(width=600, height=300, background_color='white', colormap='viridis').generate(text)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')  # No axes for word cloud
    plt.tight_layout()
    plt.savefig('static/word_cloud.png')  # Save the plot to a file
    plt.close()

# Function to generate a word cloud for a specific user
def generate_word_cloud(user, user_df):
    text = ' '.join(user_df['Cleaned Message'])
    wordcloud = WordCloud(width=600, height=300, background_color='white').generate(text)
    wordcloud_path = f'static/{user}_wordcloud.png'
    wordcloud.to_file(wordcloud_path)
    return wordcloud_path

# Function to analyze most active times
def plot_user_activity_times(user, user_df):
    # Ensure the 'static' folder exists for storing images
    if not os.path.exists('static'):
        os.makedirs('static')

    # Most active hours
    plt.figure(figsize=(8, 4))
    user_df['Hour'].value_counts().sort_index().plot(kind='bar', color='skyblue')
    plt.title(f'Most Active Hours for {user}')
    plt.xlabel('Hour of the Day')
    plt.ylabel('Number of Messages')
    plt.tight_layout()
    active_hours_path = f'static/{user}_active_hours.png'
    plt.savefig(active_hours_path)
    plt.close()

    # Most active days
    plt.figure(figsize=(8, 4))
    user_df['Date'].dt.day_name().value_counts().plot(kind='bar', color='orange')
    plt.title(f'Most Active Days for {user}')
    plt.xlabel('Day of the Week')
    plt.ylabel('Number of Messages')
    plt.tight_layout()
    active_days_path = f'static/{user}_active_days.png'
    plt.savefig(active_days_path)
    plt.close()

    return active_hours_path, active_days_path

@app2.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        whatsapp_df = whatsapp_data_to_dataframe(file_path)
        overall_activity = overall_analysis(whatsapp_df)

        user_activity = {user: analyze_user_activity(whatsapp_df, user) for user in whatsapp_df['User'].unique()}

        # return render_template('result.html', overall_activity=overall_activity, user_activity=user_activity, file_name=file.filename)
        # Generate visualizations and save them
        words_per_user = whatsapp_df.groupby('User')['Message'].apply(lambda x: ' '.join(x).split()).apply(len)
        media_per_user = whatsapp_df[whatsapp_df['Message'] == '<Media omitted>'].groupby('User').size()
        weekly_activity = whatsapp_df.groupby([whatsapp_df['Date'].dt.isocalendar().week, 'User']).size().unstack(fill_value=0)
        most_active_user = whatsapp_df['User'].value_counts().idxmax()

        # Generate plots and save them
        plot_user_activity(words_per_user, media_per_user, weekly_activity, most_active_user, whatsapp_df)

        return render_template(
            'result.html',
            overall_activity=overall_activity,
            user_activity=user_activity,
            file_name=file.filename,
            plots={
                'words_per_user': 'static/words_per_user.png',
                'media_per_user': 'static/media_per_user.png',
                'weekly_activity': 'static/weekly_activity.png',
                'most_active_user': 'static/most_active_user.png',
                'user_activity_distribution': 'static/user_activity_distribution.png'
            }
        )

    return render_template('index.html')

@app2.route('/user_analysis', methods=['POST'])
def user_analysis():
    user = request.form.get('username')
    file_path = os.path.join(UPLOAD_FOLDER, request.form.get('file_name'))
    
    try:
        whatsapp_df = whatsapp_data_to_dataframe(file_path)

        user_df = whatsapp_df[whatsapp_df['User'] == user]
        user_activity = analyze_user_activity(whatsapp_df, user)
        if user_activity:
            # Generate word cloud
            wordcloud_path = generate_word_cloud(user, user_df)
            # Plot most active times
            active_hours_path, active_days_path = plot_user_activity_times(user, user_df)

            # return render_template('user_result.html', user=user, user_activity=user_activity)
            return render_template(
                'user_result.html', 
                user=user, 
                user_activity=user_activity, 
                wordcloud_path=wordcloud_path,
                active_hours_path=active_hours_path,
                active_days_path=active_days_path
            )
        else:
            return f"No data found for user: {user}", 404
    except Exception as e:
        return f"An error occurred: {e}", 500

if __name__ == '__main__':
    app2.run(debug=True)
