import pandera as pa

# Schema for MTA Daily Ridership Data
mta_schema = pa.DataFrameSchema(
    {
        "date": pa.Column(
            pa.DateTime,
            nullable=False,
            checks=pa.Check.greater_than_or_equal_to("2020-03-01"),
            description="Date of ridership record, starting from March 2020",
        ),
        "subways_total_estimated_ridership": pa.Column(
            float,
            nullable=True,
            checks=pa.Check.greater_than_or_equal_to(0),
            description="Total estimated subway ridership",
        ),
        "subways_of_comparable_pre_pandemic_day": pa.Column(
            float,
            nullable=True,
            checks=[
                pa.Check.greater_than_or_equal_to(0),
                pa.Check.less_than_or_equal_to(2.0),
            ],
            description="Subway ridership as ratio of pre-pandemic levels (0 to 2.0)",
        ),
        "buses_total_estimated_ridership": pa.Column(
            float,
            nullable=True,
            checks=pa.Check.greater_than_or_equal_to(0),
            description="Total estimated bus ridership",
        ),
        "buses_of_comparable_pre_pandemic_day": pa.Column(
            float,
            nullable=True,
            checks=[
                pa.Check.greater_than_or_equal_to(0),
                pa.Check.less_than_or_equal_to(2.0),
            ],
            description="Bus ridership as ratio of pre-pandemic levels",
        ),
        "lirr_total_estimated_ridership": pa.Column(
            float,
            nullable=True,
            checks=pa.Check.greater_than_or_equal_to(0),
            description="Total estimated LIRR ridership",
        ),
        "lirr_of_comparable_pre_pandemic_day": pa.Column(
            float,
            nullable=True,
            checks=[
                pa.Check.greater_than_or_equal_to(0),
                pa.Check.less_than_or_equal_to(2.0),
            ],
            description="LIRR ridership as ratio of pre-pandemic levels",
        ),
        "metro_north_total_estimated_ridership": pa.Column(
            float,
            nullable=True,
            checks=pa.Check.greater_than_or_equal_to(0),
            description="Total estimated Metro-North ridership",
        ),
        "metro_north_of_comparable_pre_pandemic_day": pa.Column(
            float,
            nullable=True,
            checks=[
                pa.Check.greater_than_or_equal_to(0),
                pa.Check.less_than_or_equal_to(2.0),
            ],
            description="Metro-North ridership as ratio of pre-pandemic levels",
        ),
        "bridges_and_tunnels_total_traffic": pa.Column(
            float,
            nullable=True,
            checks=pa.Check.greater_than_or_equal_to(0),
            description="Total bridges and tunnels traffic",
        ),
        "bridges_and_tunnels_of_comparable_pre_pandemic_day": pa.Column(
            float,
            nullable=True,
            checks=[
                pa.Check.greater_than_or_equal_to(0),
                pa.Check.less_than_or_equal_to(2.0),
            ],
            description="B&T traffic as ratio of pre-pandemic levels",
        ),
    },
    coerce=True,
)


def validate_mta_data(df):
    """Validate MTA ridership dataframe against schema."""
    return mta_schema.validate(df)
