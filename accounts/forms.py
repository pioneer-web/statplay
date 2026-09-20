from django import forms

from accounts.models import User


class SignupForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput,
    )

    password2 = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User

        fields = [
            "name",
            "email",
            "phone",
        ]

        labels = {
            "name": "Nome",
            "email": "E-mail",
            "phone": "Telefone",
        }

    def clean(self):
        cleaned = super().clean()

        if (
            cleaned.get("password1")
            != cleaned.get("password2")
        ):
            self.add_error(
                "password2",
                "As senhas não coincidem.",
            )

        return cleaned

    def save(self, commit=True):
        user = super().save(
            commit=False
        )

        user.set_password(
            self.cleaned_data[
                "password1"
            ]
        )

        if commit:
            user.save()

        return user
