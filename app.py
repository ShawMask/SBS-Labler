from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import random
import csv
import os
from urllib.parse import urlencode
import json

app = Flask(__name__)

# Load the dataset to label
df = pd.read_csv("data/unlabeled_one_attribute.csv")
df = df.dropna(subset=["story", "traits", "Model"])
stories = df.to_dict(orient="records")

REQUIRED_LABELS = 50

USERS_FILE = "users.csv"
LABELS_FILE = "labeled_data.csv"

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    df_users = pd.read_csv(USERS_FILE)
    return df_users.set_index("StudentID").to_dict(orient="index")

def save_user(user):
    users = load_users()
    users[user["student_id"]] = user
    df_users = pd.DataFrame.from_dict(users, orient="index")
    df_users.to_csv(USERS_FILE, index_label="StudentID")

def count_user_labels(student_id):
    if not os.path.exists(LABELS_FILE):
        return 0
    df_labels = pd.read_csv(LABELS_FILE)
    return len(df_labels[df_labels["StudentID"] == student_id])
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form["name"].strip()
        family = request.form["family"].strip()
        student_id = request.form["student_id"].strip()

        users = load_users()  # from users.csv
        user = users.get(student_id)

        if user and user.get("demographics_done") in [True, "True", "true", "yes"]:
            # if user and user.get("demographics_done") == "yes":
            # They've already done demographics
            return redirect(f"/label?{urlencode({'name': name, 'family': family, 'student_id': student_id})}")
        else:
            # First time — do demographics
            return redirect(f"/demographics?{urlencode({'name': name, 'family': family, 'student_id': student_id})}")

    return render_template("login.html")
@app.route("/demographics", methods=["GET", "POST"])
def demographics():
    name = request.args.get("name", "")
    family = request.args.get("family", "")
    student_id = request.args.get("student_id", "")

    if request.method == "POST":
        proficiency = request.form.get("proficiency")
        consent = request.form.get("consent") == "on"
        age = request.form.get("age", "")
        gender = request.form.get("gender", "")
        field = request.form.get("field", "")

        # if not consent:
        #     return "Consent is required to participate.", 400


        # Save user info with demographics done as "yes"
        user = {
            "name": name,
            "family": family,
            "student_id": student_id,
            "age": age,
            "gender": gender,
            "proficiency": proficiency,
            "field": field,
            "consent": "Yes",
            "demographics_done": "yes"
        }
        save_user(user)

        return redirect(f"/label?{urlencode({'name': name, 'family': family, 'student_id': student_id})}")

    return render_template("demographics.html", name=name, family=family, student_id=student_id)

@app.route("/label", methods=["GET", "POST"])
def label():
    # Get user info from query params
    name = request.args.get("name")
    family = request.args.get("family")
    student_id = request.args.get("student_id")

    if not (name and family and student_id):
        # If user info missing, force login
        return redirect(url_for("login"))

    # Load user from users.csv to get demographic info and consent
    users = load_users()
    user = users.get(student_id)
    if not user or not user.get("demographics_done"):
        # Demographics not done? Send to demographics page
        query = urlencode({
            "name": name,
            "family": family,
            "student_id": student_id
        })
        return redirect(f"/demographics?{query}")

    completed = count_user_labels(student_id)
    left = max(0, REQUIRED_LABELS - completed)
    if left == 0:
        return f"Thank you, {name}! You have completed your labeling assignment."

    if request.method == "POST":
        row = [
            name, family, student_id,
            user.get("age", ""),
            user.get("gender", ""),
            user.get("proficiency", ""),
            user.get("field", ""),
            user.get("consent", "No"),
            request.form["model"],
            request.form["story"],
            request.form["attribute"],
            request.form["attr_sentiment"],
            request.form["stereotype"],
            request.form["attr_exists"],
            request.form["alt_attribute"],
            request.form["main_gender"],
            request.form["char_count"],
            request.form["performer_is_main"],
            request.form["performer_gender"],
            request.form["receiver_gender"],
            request.form["ending"],
            request.form["tone"],
            request.form["coherence"],
            request.form["understandable"],
            request.form["quality"],
            request.form.get("cleaned_story", "").strip(),
            request.form.get("start_time", ""),
            request.form.get("label_duration", ""),
        ]
        file_exists = os.path.exists(LABELS_FILE)
        with open(LABELS_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "Name", "Family", "StudentID", "Age", "Gender", "EnglishProficiency", "FieldOfStudy", "Consent",
                    "Model", "Story", "Attribute", "AttributeSentiment", "GenderStereotype", "AttrExists", "AltAttribute",
                    "MainGender", "CharCount", "PerformerIsMain", "PerformerGender", "ReceiverGender",
                    "Ending", "Tone", "Coherence", "ChildrenUnderstandable", "ChildQuality", "CleanedStory", "StartTime", "LabelDuration",
                ])
            writer.writerow(row)

        # Redirect to label with same user info to continue
        query = urlencode({
            "name": name,
            "family": family,
            "student_id": student_id
        })
        return redirect(f"/label?{query}")

    # Pick a random story not yet labeled by this user
    # Filter out already labeled stories by this user (optional, can be improved)
    # For now just pick any random sample

    # You can extend to exclude already labeled items for user if needed

    sample = random.choice(stories)
    story = sample["story"]
    attribute = sample["traits"]
    model = sample["Model"]

    with open("data/attribute_definition.json", "r") as f:
        attribute_definitions = json.load(f)

    definition = attribute_definitions.get(attribute, "No definition available.")

    return render_template("label.html",
                           story=story,
                           attribute=attribute,
                           model=model,
                           user=user,
                           completed=completed,
                           total_required=REQUIRED_LABELS,
                           definition=definition,
                           )

if __name__ == "__main__":
    import os
    import threading
    import webbrowser
    port = int(os.environ.get("PORT", 5000))
    threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    app.run(host="0.0.0.0", port=port, debug=True)
