# TDR-0007: SSH-Zugang über einen WireGuard-Tunnel

* **Status:** accepted
* **Date:** 2026-10-13
* **Author:** Nicolas Mischler
* **Scope:** Server-Zugang (`ops/server/cloud-init.yaml`, Cloud-Firewall), Runbook

## Problem / Scope

Die Cloud-Firewall liess SSH (TCP 22) nur von einer festen Adresse zu. Der Anschluss der
administrierenden Person hat aber eine wechselnde IP, und unterwegs (Handy-Hotspot, Zug) wechselt
sie ständig – der Zugang brach regelmässig weg. SSH für alle zu öffnen hätte eine Schutzschicht
entfernt (Port 22 wird laufend von Bots abgeklopft).

## Technical Decision

* WireGuard-Tunnel Laptop ↔ Server (Point-to-Point, privates Netz `10.66.0.0/24`, Server `.1`).
  Nur Verkehr zum Server läuft durch den Tunnel (Split-Tunnel, `AllowedIPs` = Serveradresse).
* Cloud-Firewall: TCP 22 von aussen geschlossen, UDP `51820` offen. WireGuard antwortet nur auf
  Pakete mit gültigem Schlüssel – für Scanner ist der Port stumm.
* `ufw` lässt TCP 22 (mit `limit`) weiter zu: Im Notfall genügt es, in der Cloud-Firewall
  vorübergehend eine Regel für die aktuelle Adresse anzulegen (kein Rescue-System nötig).
* SSH-Härtung bleibt unverändert (nur Schlüssel, kein Root, nur `deploy`, fail2ban).
* Ein Schlüsselpaar pro Gerät; verlorene Geräte werden durch Entfernen des Peers gesperrt.
  Schlüssel und Adressen stehen nur auf den Geräten bzw. im verschlüsselten Runbook.

## Rationale & Trade-offs

* **Why this approach:** funktioniert hinter jedem NAT/Hotspot (`PersistentKeepalive`), kein
  Drittanbieter und kein Konto, im Ubuntu-Kernel enthalten, ein einziger UDP-Port.
* **Alternatives evaluated:** IP-Regel bei Bedarf anpassen (Handarbeit bei jedem Wechsel, unterwegs
  unpraktisch); SSH für alle öffnen (eine Schutzschicht weniger); Mesh-VPN-Dienst (bequemer, aber
  abhängig von einem externen Koordinationsdienst und Konto).
* **Impact on existing code:** keiner an der Anwendung. Netze, die UDP blockieren (manche Firmen-
  oder Hotel-WLANs), erfordern den Handy-Hotspot oder den Notweg über die Cloud-Firewall. Das
  automatische Deployment (ADR-0005) braucht kein SSH und ist nicht betroffen.
