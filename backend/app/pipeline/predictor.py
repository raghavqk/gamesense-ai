import torch
import torch.nn as nn


class KDLSTM(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(3, 64, 2, batch_first=True, dropout=0.2)
        self.fc = nn.Sequential(nn.Linear(64, 16), nn.ReLU(), nn.Linear(16, 2))

    def forward(self, x):
        o, _ = self.lstm(x)
        return self.fc(o[:, -1])


def lstm_predict(vision: dict) -> dict:
    k = vision.get("kills", 0)
    d = vision.get("deaths", 1)
    hs = vision.get("headshot_pct", 0) / 100.0
    kd = k / max(1, d)

    seq = torch.tensor(
        [[[k * 0.2 * i, d * 0.2 * i, hs] for i in range(1, 6)]],
        dtype=torch.float32,
    )

    model = KDLSTM()
    model.eval()
    with torch.no_grad():
        pred = model(seq)[0]

    pk = max(0.0, float(pred[0]))
    pd = max(0.01, float(pred[1]))
    pred_kd = round(kd * 0.65 + pk / pd * 0.35, 2)

    return {
        "predicted_kills": round(pk, 2),
        "predicted_deaths": round(pd, 2),
        "predicted_kd": pred_kd,
    }
