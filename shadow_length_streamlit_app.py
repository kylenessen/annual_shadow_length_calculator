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


def date_range(start, end, delta):
    list = []
    curr = start
    while curr < end:
        list.append(curr)
        curr += delta
    return list


st.header('Annual Shadow Length Ratio Calculator')
st.write(''' Shadow length ratio refers to how long a shadow is relative to the object casting it. A value of `1.0` means the length of the shadow is equal to the height of the object. Smaller values (e.g. `0.5`) correspond to shorter shadows, and larger values (e.g. `5.0`) represent longer shadows.''')
st.image('https://www.researchgate.net/publication/220541439/figure/fig7/AS:668676479012870@1536436304332/The-relationship-between-the-sun-elevation-e-object-height-H-and-shadow-length-L.png')
st.write('Excessive shadowing in your imagery can be detrimential to your data quality, depending on your application. This calculator is intended to help you plan for future projects where the angle of the sun is important.')
st.subheader('Parameters')
st.caption(
    'Please enter your information below. Examples are provided, but please change as needed.')
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
                            total=len(daterange), desc="Please wait. This will take several moments."):
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
            sns.heatmap(pivot, annot=True, linewidths=.5, ax=ax, cmap='rocket')
            ax.set(xlabel='', ylabel='Hour of day',
                   title='''Number of days where shadow length ratio is less than {shadow}
                {address}'''.format(shadow=max_shadow_length, address=address))
            st.header('Results')
            st.pyplot(fig=plot)
            st.write('Each cell represnts the number of days within the corresponding month and hour that meet the shadow length criteria. For example, if the cell corresponding to "June" and "12" has a value of "30, then everyday that month at 12PM the sun was high enough to meet criteria. If months are missing in your graph, particularly in the winter time, then no hours during the day had short enough shadows.')
