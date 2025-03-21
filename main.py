import streamlit as st
import pandas as pd
import plotly.express as px
from wordcloud import WordCloud
from collections import Counter
import plotly.graph_objs as go
import networkx as nx
def analyze_tweet_engagement(data):
    # Check if required columns are present
    required_columns = {'username', 'post_id', 'like_count', 'comment_count', 'view_count'}
    if required_columns.issubset(data.columns):
        # Fill NaN values and convert to float
        data[['like_count', 'comment_count', 'view_count']] = data[['like_count', 'comment_count', 'view_count']].fillna(0).astype(float)

        # Calculate total engagement for all posts
        data['total_engagement'] = data['like_count'] + data['comment_count'] + data['view_count']

        # Get top 5 users by total like count
        top_users = data.groupby('username')['like_count'].sum().nlargest(5).index.tolist()

        # Ensure each row in the dataframe represents a unique user-post pair
        # Create a unique identifier for each user-post pair
        data['pair_id'] = data['username'] + '_' + data['post_id'].astype(str)

        # Create a list of all unique user-post pairs
        all_pairs = []
        for _, row in data.iterrows():
            pair_text = f"{row['username']} (Post: {row['post_id']}) - Likes: {int(row['like_count'])}, Comments: {int(row['comment_count'])}, Views: {int(row['view_count'])}"
            all_pairs.append(pair_text)

        # Get default selections - best post for each top user
        default_posts = []
        for user in top_users:
            # Get the highest engagement post for this user
            best_post = data[data['username'] == user].sort_values('like_count', ascending=False).iloc[0]
            pair_text = f"{best_post['username']} (Post: {best_post['post_id']}) - Likes: {int(best_post['like_count'])}, Comments: {int(best_post['comment_count'])}, Views: {int(best_post['view_count'])}"
            default_posts.append(pair_text)

        # User selects username-post pairs using multiselect
        selected_pairs = st.multiselect(
            "Select Users and Posts to Visualize Engagement Metrics",
            options=all_pairs,
            default=default_posts,  # Default to top 5 users' best posts
            help="Select one or more user-post pairs to visualize their engagement metrics."
        )

        if selected_pairs:
            # Extract username and post_id from selection
            selected_users_posts = []

            for pair in selected_pairs:
                # Split the string to extract username and post_id
                username = pair.split(" (Post: ")[0]
                post_id = pair.split(" (Post: ")[1].split(")")[0]
                selected_users_posts.append((username, post_id))

            # Filter the dataframe for selected user-post pairs
            filtered_data = data[
                data.apply(lambda row: any((row['username'] == user and str(row['post_id']) == post)
                                            for user, post in selected_users_posts), axis=1)
            ]

            # Create a unique identifier for radar chart
            filtered_data['identifier'] = filtered_data['username'] + " (Post: " + filtered_data['post_id'].astype(str) + ")"

            # Check if we actually have data for the selected pairs
            if len(filtered_data) > 0:
                # Extract only the metrics for normalization
                metrics_df = filtered_data[['identifier', 'like_count', 'comment_count', 'view_count']].set_index('identifier')

                # Calculate maximum values for each metric for normalization
                max_values = metrics_df.max()

                # Avoid division by zero
                for col in max_values.index:
                    if max_values[col] == 0:
                        max_values[col] = 1

                # Normalize the metrics
                normalized_metrics = metrics_df / max_values

                # Create spider chart
                st.markdown("### Engagement Metrics for Selected Posts")
                fig_engagement_spider = go.Figure()

                for idx in normalized_metrics.index:
                    fig_engagement_spider.add_trace(go.Scatterpolar(
                        r=normalized_metrics.loc[idx].values,
                        theta=['Likes', 'Comments', 'Views'],
                        fill='toself',
                        name=idx
                    ))

                fig_engagement_spider.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 1]  # Normalized range
                        ),
                        angularaxis=dict(tickfont=dict(size=10))
                    ),
                    title="Post Engagement",
                    template='plotly_dark',
                    showlegend=True
                )
                st.plotly_chart(fig_engagement_spider)
            else:
                st.write("No data found for the selected user-post pairs.")
        else:
            st.write("No user-post pairs selected. Please select at least one pair.")
    else:
        st.write("Required columns are missing in the dataframe.")

# Function to create a post creation timeline as an area chart
def create_timeline(data):
    # Convert Unix epoch time to datetime
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='s')
    timeline = data.groupby(data['timestamp'].dt.date).size().reset_index(name='count')

    fig = px.area(timeline, x='timestamp', y='count', title='Post Creation Timeline',
                  labels={'timestamp': 'Date', 'count': 'Number of Posts'},
                  template='plotly_dark')
    fig.update_traces(line_color='#1f77b4', fillcolor='rgba(31, 119, 180, 0.2)')
    fig.update_layout(yaxis_title='Number of Posts')
    st.plotly_chart(fig)

# Function to create a word cloud
def create_wordcloud(text, title):
    wordcloud = WordCloud(width=800, height=400, background_color='white',font_path='JustAnotherHand-Regular.ttf').generate(text)
    fig = px.imshow(wordcloud, template='plotly_dark', title=title )
    fig.update_xaxes(showticklabels=False)
    fig.update_yaxes(showticklabels=False)
    st.plotly_chart(fig)

def analyze_post_frequency(data):
    post_frequency = data['username'].value_counts().head(20)
    fig = px.bar(post_frequency, title='Top 20 Users by Post Frequency',
                 labels={'index': 'Username', 'value': 'Number of Posts'},
                 template='plotly_dark')
    st.plotly_chart(fig)
# Function to create a bar chart
def create_bar_chart(data, title, xlabel, ylabel):
    fig = px.bar(data, x=data.index, y=data.values, title=title,
                 labels={xlabel: xlabel, 'value': ylabel},
                 template='plotly_dark')
    fig.update_layout(yaxis_title=ylabel)
    st.plotly_chart(fig)
def create_heatmap(data):
    # Convert Unix epoch time to datetime
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='s')
    data['day_of_week'] = data['timestamp'].dt.day_name()
    data['hour'] = data['timestamp'].dt.hour

    # Create a pivot table for the heatmap and fill NaN values with 0
    heatmap_data = data.pivot_table(index='day_of_week', columns='hour', aggfunc='size', fill_value=0)

    # Ensure all days of the week and hours are present
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    hours = list(range(24))
    heatmap_data = heatmap_data.reindex(index=days_order, columns=hours, fill_value=0)

    fig = px.imshow(heatmap_data, aspect="auto", title='Heatmap of Posts by Day of Week and Hour',
                    labels=dict(x="Hour of Day", y="Day of Week", color="Number of Posts"),
                    template='plotly_dark', color_continuous_scale="Viridis")
    st.plotly_chart(fig)

# Streamlit app
def main():
    st.title('Social Media Post Analysis')

    # Upload CSV file
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file is not None:
        # Load data
        data = pd.read_csv(uploaded_file)

        # Post creation timeline
        st.subheader('Post Creation Timeline')
        create_timeline(data)
        
        # Word cloud of captions
        st.subheader('Word Cloud of Captions')
        captions = ' '.join(data['caption'].dropna().astype(str))
        create_wordcloud(captions, 'Word Cloud of Captions')
        
        st.subheader('Heatmap of Posts by Day of Week and Hour')
        create_heatmap(data)
        # Word cloud of hashtags
        st.subheader('Word Cloud of Hashtags')
        hashtags = ' '.join(data['hashtags'].dropna().astype(str))
        create_wordcloud(hashtags, 'Word Cloud of Hashtags')
        

        analyze_tweet_engagement(data)
        # Top 20 users by number of posts
        st.subheader('Top 20 Users by Number of Posts')
        top_users = data['username'].value_counts().head(20)
        create_bar_chart(top_users, 'Top 20 Users', 'Username', 'Number of Posts')

        # Top 20 mentions
        st.subheader('Top 20 Mentions')
        mentions = ' '.join(data['mentions'].dropna().astype(str)).split()
        top_mentions = Counter(mentions).most_common(20)
        top_mentions_df = pd.DataFrame(top_mentions, columns=['Mention', 'Count']).set_index('Mention')
        create_bar_chart(top_mentions_df['Count'], 'Top 20 Mentions', 'Mention', 'Count')


if __name__ == '__main__':
    main()
