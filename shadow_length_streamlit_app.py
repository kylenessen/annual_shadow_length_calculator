import math
import seaborn as sns
import pytz
import pandas as pd
from pysolar.solar import *
from datetime import *
import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from tzwhere import tzwhere
from matplotlib import pyplot as plt
from stqdm import stqdm


def get_location_info(address):
    geolocator = Nominatim(user_agent="GTA Lookup")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    location = geolocator.geocode(address)
    return location.latitude, location.longitude


def date_to_datetime(dt):
    return datetime(dt.year, dt.month, dt.day, 0, 0, 0)


def create_date_time_objects(start, end):
    timezone = tzwhere.tzwhere().tzNameAt(lat, lon)
    tz = pytz.timezone(timezone)
    start = date_to_datetime(start)
    end = date_to_datetime(end)
    start = start.replace(tzinfo=pytz.timezone(timezone))
    end = end.replace(tzinfo=pytz.timezone(timezone))
    return start, end


def format_date(date):
    return (date.strftime('%b %-d, %Y'))


def date_range(start, end, delta):
    list = []
    curr = start
    while curr < end:
        list.append(curr)
        curr += delta
    return list


st.header('Annual Shadow Length Ratio Calculator')
st.caption('''By Kyle Nessen\n
November, 2023''')
st.write(''' Shadow length ratio refers to how long a shadow is relative to the object casting it and is a helpful reference point when considering drone mapping missions. A value of `1.0` means the length of the shadow is equal to the object's height. Smaller values (e.g. `0.5`) correspond to shorter shadows, and larger values (e.g. `2.0`) represent longer shadows.''')
st.image('Shadow_length_ratio_figure.png')
st.write('Considering shadow length ratio during the mission planning stages can be helpful, as excessive shadowing can degrade the quality of your imagery and final downstream products. This calculator is intended to help you plan for future projects where consistent lighting conditions are important to review.')
st.subheader('Parameters')
st.caption(
    'Please enter your project-specific information below. Examples are provided, but please change them as needed. This app will return all hours where the shadow length ratio is less than the maximum. Change the max value to something very large (e.g. `100`) to see all daylight hours.')
with st.form(key='my form'):
    address = st.text_input("Address, City, or Region", "New Orleans, LA")
    start = st.date_input('Start Date', value=(datetime(2023, 1, 1)))
    end = st.date_input('End Date', value=datetime(2024, 1, 1))
    max_shadow_length = st.number_input(
        'Max shadow length ratio', value=1.0)
    submitted = st.form_submit_button("Submit")

if submitted:
    if start > end:
        st.subheader(
            'Start date must be before end date. Please fix and try again')
        submitted = False
    else:
        st.caption('Parsing location...')
        lat, lon = get_location_info(address)
        start, end = create_date_time_objects(start, end)
        map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})

        delta = timedelta(minutes=10)
        output = []

        st.caption('Location found:')
        st.map(map_data, use_container_width=True)
        st.caption('Calculating shadow length...')
        daterange = date_range(start, end, delta)
        for result in stqdm(daterange,
                            total=len(daterange)):
            angle = get_altitude(lat, lon, result)
            shadow_length = 1 / math.tan(angle * math.pi / 180)
            month = result.month
            hour = result.strftime('%H')
            week = result.strftime("%V")
            if shadow_length > 0 and shadow_length < max_shadow_length:
                output.append(
                    [result, angle, month, week, hour, shadow_length])

        if len(output) == 0:
            st.subheader(
                'Your search did not return any results that meet your criteria. Please change the parameters and try again.')
        else:
            df = pd.DataFrame(
                output, columns=['time', 'angle', 'month', 'week', 'hour', 'shadow'])

            pivot = pd.pivot_table(df, values='shadow', index='hour',
                                   columns='month', aggfunc='count')
            pivot = pivot.fillna(0)
            pivot = round(pivot / 6, 0)
            pivot = pivot.sort_index(ascending=False)

            columns = {1: 'Jan',
                       2: 'Feb',
                       3: 'Mar',
                       4: 'Apr',
                       5: 'May',
                       6: 'Jun',
                       7: 'Jul',
                       8: 'Aug',
                       9: 'Sep',
                       10: 'Oct',
                       11: 'Nov',
                       12: 'Dec'}
            pivot = pivot.rename(columns=columns)

            plot, ax = plt.subplots(figsize=(8.5, 6))
            sns.heatmap(pivot, annot=True, linewidths=.5,
                        ax=ax, cmap='Blues_r')
            ax.set(xlabel='', ylabel='Hour of day',
                   title='''Number of days where shadow length ratio is less than {shadow}
                {address}
                {start} - {end}'''.format(shadow=max_shadow_length, address=address, start=format_date(start), end=format_date(end)))
            st.header('Results')
            st.pyplot(fig=plot)
            st.caption('Each cell represents the number of days where the shadow length ratio was less than the maximum specified for any given hour of the day per month. For example, if the cell corresponding to `Jun` and `12` has a value of `30`, then every day that month at noon, the sun was high enough to meet the criteria. If months or hours are missing in your graph, then conditions were never met and are omitted (e.g. midnight in January). All days are rounded to the nearest integer, so cells with a value of `0` indicate that less than 30 mins met criteria.')
