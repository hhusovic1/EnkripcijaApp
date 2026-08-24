"""
MITM demo na neautentifikovani Diffie-Hellman. Vidi thesis 3.4.4.

Tri strane dijele isti "kanal" objekat - Mallory ga kontrolise i moze
presresti/zamijeniti poruke, a Alice i Bob ne primjecuju nista.
"""


class Channel:
    """Simulira nesiguran komunikacioni kanal."""

    def __init__(self):
        self.last_message = None

    def send(self, message):
        self.last_message = message

    def receive(self):
        return self.last_message


class Party:
    def __init__(self, name, channel, p, g):
        self.name = name
        self.channel = channel
        self.p = p
        self.g = g
        self.private_key = None  # TODO: nasumican tajni eksponent
        self.shared_secret = None

    def generate_and_send_public_value(self):
        """TODO: izracunaj g^a mod p i posalji preko kanala."""
        raise NotImplementedError

    def compute_shared_secret(self, their_public_value):
        """TODO: izracunaj (njihova_vrijednost)^moj_privatni mod p."""
        raise NotImplementedError


class Mallory:
    """Napadac - presrece i zamjenjuje javne vrijednosti obje strane."""

    def __init__(self, channel_alice, channel_bob, p, g):
        raise NotImplementedError  # TODO: implementiraj presretanje


if __name__ == "__main__":
    # TODO 1: postavi Alice i Bob BEZ Mallory - pokazi da rade normalno
    # TODO 2: isti scenario SA Mallory - pokazi da oboje "misle" da razgovaraju
    #         direktno, a Mallory cita sve
    pass
