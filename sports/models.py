from django.db import models
class Sport(models.Model):
    name=models.CharField(max_length=80); slug=models.SlugField(unique=True); active=models.BooleanField(default=True)
    def __str__(self): return self.name
class Competition(models.Model):
    sport = models.ForeignKey(
        Sport,
        on_delete=models.CASCADE,
    )

    name = models.CharField(
        max_length=120
    )

    country = models.CharField(
        max_length=80,
        blank=True,
    )

    external_id = models.CharField(
        max_length=120,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "sport",
                    "external_id",
                ],
                condition=~models.Q(
                    external_id=""
                ),
                name=(
                    "unique_sport_competition_external_id"
                ),
            )
        ]

    def __str__(self):
        return self.name
class Team(models.Model):
    sport=models.ForeignKey(Sport,on_delete=models.CASCADE); name=models.CharField(max_length=120); external_id=models.CharField(max_length=120,blank=True)
    def __str__(self): return self.name
class Event(models.Model):
    STATUS = [
        ("scheduled", "Agendado"),
        ("live", "Ao vivo"),
        ("finished", "Finalizado"),
        ("cancelled", "Cancelado"),
    ]

    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
    )

    home_team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="home_events",
    )

    away_team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="away_events",
    )

    starts_at = models.DateTimeField(
        db_index=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="scheduled",
    )

    external_id = models.CharField(
        max_length=120,
        blank=True,
        db_index=True,
    )

    home_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    away_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "external_id",
                ],
                condition=~models.Q(
                    external_id=""
                ),
                name=(
                    "unique_event_external_id"
                ),
            )
        ]

    def __str__(self):
        return (
            f"{self.home_team} "
            f"x {self.away_team}"
        )
class TeamMatchStats(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="team_stats",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
    )

    corners = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    shots = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    shots_on_target = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    possession = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    cards = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    xg = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "team"],
                name="unique_event_team_stats",
            )
        ]

    def __str__(self):
        return f"{self.event} - {self.team}"


class Player(models.Model):
    sport = models.ForeignKey(
        Sport,
        on_delete=models.CASCADE,
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="players",
    )
    external_id = models.CharField(
        max_length=120,
        db_index=True,
    )
    name = models.CharField(
        max_length=160,
    )
    position = models.CharField(
        max_length=10,
        blank=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "sport",
                    "external_id",
                ],
                name="unique_sport_player_external_id",
            )
        ]

    def __str__(self):
        return self.name


class PlayerMatchStats(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="player_stats",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
    )
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name="match_stats",
    )

    position = models.CharField(
        max_length=10,
        blank=True,
    )

    started = models.BooleanField(
        default=False,
    )
    substitute = models.BooleanField(
        default=False,
    )

    minutes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    goals = models.PositiveSmallIntegerField(
        default=0,
    )
    assists = models.PositiveSmallIntegerField(
        default=0,
    )

    xg = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        null=True,
        blank=True,
    )
    xa = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        null=True,
        blank=True,
    )

    shots = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    shots_on_target = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    saves = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    rating = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )

    #
    # Gols sofridos pelo TIME nessa partida.
    # Não estamos fingindo que todos ocorreram
    # enquanto o jogador estava em campo.
    #
    team_goals_conceded = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    clean_sheet = models.BooleanField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "event",
                    "player",
                ],
                name="unique_event_player_stats",
            )
        ]

        indexes = [
            models.Index(
                fields=[
                    "player",
                    "-event",
                ]
            )
        ]


class EventLineupPlayer(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="lineup_players",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
    )
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
    )

    position = models.CharField(
        max_length=10,
        blank=True,
    )

    starter = models.BooleanField(
        default=False,
    )
    substitute = models.BooleanField(
        default=False,
    )
    confirmed = models.BooleanField(
        default=False,
    )

    captured_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "event",
                    "player",
                ],
                name="unique_event_lineup_player",
            )
        ]
