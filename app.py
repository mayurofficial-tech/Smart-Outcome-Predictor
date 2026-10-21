import json
from pathlib import Path

import joblib
import pandas as pd
import streamlit  as st

# Project PAth

base_path = Path().cwd()
schema_path = base_path/"outputs"/"input_schema.json"

classifier_path = base_path/"model"/"best_classifiction_model.pkl"

regressor_path = base_path/"model"/"best_regression_model.pkl"


@st.cache_data
def load_schema(path):
    with open(path, "r",encoding = "utf-8") as file:
        return json.load(file)


@st.cache_resource
def load_model(path):
    return joblib.load(path)


st.set_page_config(
    page_title="Smarrt Outcome Predictor",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 Smart Outcome Predictor")
st.write(
    "Enter student and course details to predict course completion "
    "and estimate the final score."
)

schema_file = schema_path
classifier_file = classifier_path
regressor_file = regressor_path


schema = load_schema(str(schema_file))
classifier = load_model(str(classifier_file))
regressor = load_model(str(regressor_file))


st.subheader("Student details")
st.caption("Numeric fields use training-data ranges; categorical fields use values from the training data.")

with st.form("student_input_form"):
    user_data = {}
    numeric_cols = [
        col for col,info in schema.items()
        if info.get("type") == "numeric"
    ]

    categorical_cols = [
        col for col,info in schema.items()
        if info.get("type") == "categorical"
    ]

    left,right = st.columns(2)
    columns = [left,right]

    for i,col in enumerate(numeric_cols):
        info = schema[col]
        minimum = float(info.get("min",0.0))
        maximum = float(info.get("max",100.0))
        default = float(info.get("default",0.0))


        # Streamlit requires a valid range and the default must be inside it.
        if minimum > maximum:
            minimum,maximum = maximum,minimum
        if minimum==maximum:
            user_data[col]=columns[i%2].number_input(
                col,value=minimum,key=f"num_{col}"
            )
        else:
            default = min(max(default,minimum),maximum)
            user_data[col] = columns[i % 2].number_input(
                col,
                min_value=minimum,
                max_value=maximum,
                value=default,
                key=f"num_{col}",
            )

    for i, col in enumerate(categorical_cols):
        info = schema[col]
        choices = [str(value) for value in info.get("choices", [])]
        default = str(info.get("default", choices[0] if choices else "Unknown"))

        if not choices:
            choices = [default]
        if default not in choices:
            choices.insert(0, default)

        user_data[col] = columns[i % 2].selectbox(
            col,
            options=choices,
            index=choices.index(default),
            key=f"cat_{col}",
        )

    submitted = st.form_submit_button("Predict outcomes", type="primary")

if submitted:
    input_df = pd.DataFrame([user_data])

    # Use the same feature names and order as the saved schema.
    input_df = input_df[list(schema.keys())]

    try:
        completion_prediction = classifier.predict(input_df)[0]
        score_prediction = float(regressor.predict(input_df)[0])

        result_col1, result_col2 = st.columns(2)

        with result_col1:
            st.subheader("Course completion")
            if hasattr(classifier, "predict_proba"):
                probabilities = classifier.predict_proba(input_df)[0]
                classes = classifier.classes_
                positive_index = list(classes).index(1) if 1 in classes else None
                if positive_index is not None:
                    probability = float(probabilities[positive_index])
                    st.metric("Completion probability", f"{probability:.1%}")
            if completion_prediction == 1:
                st.success("Prediction: Course completed")
            else:
                st.warning("Prediction: Course not completed")

        with result_col2:
            st.subheader("Final score")
            score_prediction = max(0.0, min(100.0, score_prediction))
            st.metric("Predicted final score", f"{score_prediction:.2f} / 100")

        st.caption(
            "These are model estimates, not guarantees. Use them as decision-support "
            "information alongside educator judgment."
        )

    except Exception as exc:
        st.error(
            "Prediction failed. Check that the schema columns match the features "
            "used when the models were trained and exported."
        )
        st.exception(exc)