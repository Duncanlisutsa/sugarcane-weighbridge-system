from django import forms
from .models import Farmer, Vehicle, WeighingTransaction


# ─────────────────────────────────────────
# STEP 1 FORM — Farmer, Vehicle, Gross Weight
# ─────────────────────────────────────────
class GrossWeightForm(forms.Form):

    farmer = forms.ModelChoiceField(
        queryset=Farmer.objects.all(),
        empty_label="-- Select Farmer --",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    vehicle = forms.ModelChoiceField(
        queryset=Vehicle.objects.all(),
        empty_label="-- Select Vehicle --",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    gross_weight_kg = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class':       'form-control',
            'placeholder': 'Enter gross weight in kg',
            'step':        '0.01'
        })
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class':       'form-control',
            'placeholder': 'Optional notes',
            'rows':        2
        })
    )


# ─────────────────────────────────────────
# STEP 2 FORM — Tare Weight
# ─────────────────────────────────────────
class TareWeightForm(forms.Form):

    tare_weight_kg = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class':       'form-control',
            'placeholder': 'Enter tare weight in kg',
            'step':        '0.01'
        })
    )

    def __init__(self, gross_weight=None, *args, **kwargs):
        self.gross_weight = gross_weight
        super().__init__(*args, **kwargs)

    def clean_tare_weight_kg(self):
        tare = self.cleaned_data.get('tare_weight_kg')
        if self.gross_weight and tare >= self.gross_weight:
            raise forms.ValidationError(
                f"Tare weight ({tare} kg) must be less than "
                f"gross weight ({self.gross_weight} kg)."
            )
        return tare


# ─────────────────────────────────────────
# FARMER REGISTRATION FORM
# ─────────────────────────────────────────
class FarmerForm(forms.ModelForm):
    class Meta:
        model  = Farmer
        fields = ['full_name', 'id_number', 'phone', 'email', 'zone']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'placeholder': 'Full name'
            }),
            'id_number': forms.TextInput(attrs={
                'placeholder': 'National ID number'
            }),
            'phone': forms.TextInput(attrs={
                'placeholder': '07XXXXXXXX'
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'farmer@example.com (optional)'
            }),
            'zone': forms.TextInput(attrs={
                'placeholder': 'e.g. Zone A'
            }),
        }


# ─────────────────────────────────────────
# VEHICLE REGISTRATION FORM
# ─────────────────────────────────────────
MAKE_MODEL_CHOICES = [
    ('', '-- Select Make/Model --'),
    ('ISUZU', 'ISUZU'),
    ('MAHINDRA', 'MAHINDRA'),
    ('NEW HOLLAND', 'NEW HOLLAND'),
    ('JOHN DEERE', 'JOHN DEERE'),
    ('MASSEY FERGUSSON', 'MASSEY FERGUSSON'),
    ('Other', 'Other (type below)'),
]


class VehicleForm(forms.ModelForm):
    field_order = ['plate_number', 'make_model', 'make_model_other', 'farmer']

    make_model = forms.ChoiceField(
        choices=MAKE_MODEL_CHOICES,
        widget=forms.Select(attrs={'id': 'id_make_model'})
    )

    make_model_other = forms.CharField(
        required=False,
        label='Make/Model (if Other)',
        widget=forms.TextInput(attrs={
            'id':          'id_make_model_other',
            'placeholder': 'Enter make/model'
        })
    )

    class Meta:
        model  = Vehicle
        fields = ['plate_number', 'make_model', 'farmer']
        widgets = {
            'plate_number': forms.TextInput(attrs={
                'placeholder': 'e.g. KCA 123A'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        make_model = cleaned_data.get('make_model')
        other = cleaned_data.get('make_model_other')

        if make_model == 'Other':
            if not other:
                self.add_error(
                    'make_model_other',
                    'Please specify the make/model.'
                )
            else:
                cleaned_data['make_model'] = other

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.make_model = self.cleaned_data.get('make_model')
        if commit:
            instance.save()
        return instance