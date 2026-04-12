from __future__ import annotations

from django import forms


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)


class LLMAssistantForm(forms.Form):
    question = forms.CharField(
        label="Question",
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Who won the 2008 Australian Grand Prix?"}),
        max_length=1000,
    )


class DriverForm(forms.Form):
    forename    = forms.CharField(max_length=100, label="First name")
    surname     = forms.CharField(max_length=100, label="Last name")
    constructor_id = forms.ChoiceField(choices=[], label="Team", required=False)
    code        = forms.CharField(max_length=3,   label="Code (3 letters)", required=False)
    number      = forms.IntegerField(required=False, label="Permanent number")
    dob         = forms.DateField(
        required=False, label="Date of birth",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    nationality = forms.CharField(max_length=60, required=False)
    url         = forms.URLField(required=False,  label="Wikipedia URL")

    def __init__(self, *args, constructor_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if constructor_choices is not None:
            self.fields["constructor_id"].choices = constructor_choices


class ConstructorForm(forms.Form):
    name        = forms.CharField(max_length=150)
    nationality = forms.CharField(max_length=60, required=False)
    url         = forms.URLField(required=False, label="Wikipedia URL")


class CircuitForm(forms.Form):
    name     = forms.CharField(max_length=150)
    location = forms.CharField(max_length=100, required=False)
    country  = forms.CharField(max_length=80,  required=False)
    lat      = forms.FloatField(required=False, label="Latitude")
    lng      = forms.FloatField(required=False, label="Longitude")
    url      = forms.URLField(required=False,   label="Wikipedia URL")


class RaceForm(forms.Form):
    name       = forms.CharField(max_length=150)
    year       = forms.IntegerField(min_value=1950, max_value=2100)
    round      = forms.IntegerField(min_value=1,   label="Round number")
    circuit_id = forms.ChoiceField(choices=[], label="Circuit")
    date       = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    url        = forms.URLField(required=False, label="Wikipedia URL")

    def __init__(self, *args, circuit_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if circuit_choices:
            self.fields["circuit_id"].choices = circuit_choices


class SeasonForm(forms.Form):
    year = forms.IntegerField(min_value=1950, max_value=2100)
    url  = forms.URLField(required=False, label="Wikipedia URL")


class RaceResultsImportForm(forms.Form):
    race_id = forms.ChoiceField(choices=[], label="Race")
    csv_file = forms.FileField(label="Results CSV")

    def __init__(self, *args, race_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if race_choices is not None:
            self.fields["race_id"].choices = race_choices

    def clean_csv_file(self):
        upload = self.cleaned_data["csv_file"]
        if not upload.name.lower().endswith(".csv"):
            raise forms.ValidationError("Upload a CSV file.")
        return upload
