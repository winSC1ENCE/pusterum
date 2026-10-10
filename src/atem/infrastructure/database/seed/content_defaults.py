"""Default website content (German, Swiss spelling) – single source of truth.

Seeded into empty databases (``ContentService.seed_defaults`` / ``python -m atem.cli
seed-content``) and used as template fallback by the ``editable()`` macro. Changing a text
here does **not** update existing databases – write a data migration
(``migrations/_helpers.py:replace_default_texts``) for that.
"""

from functools import cache

DEFAULT_CONTENT_BLOCKS: list[dict[str, str]] = [
    {
        "key": "hero.badge",
        "section": "hero",
        "type": "text",
        "content": "PUSTERUM • Atem- und Körpertherapie • In Gemeinschaftspraxis Physiotherapie",
    },
    {
        "key": "hero.title",
        "section": "hero",
        "type": "text",
        "content": "PUSTERUM.",
    },
    {
        "key": "hero.subtitle",
        "section": "hero",
        "type": "text",
        "content": "Raum zum Atmen – die Brücke zwischen Körper und Psyche.",
    },
    {
        "key": "hero.text",
        "section": "hero",
        "type": "textarea",
        "content": "",
    },
    {
        "key": "hero.image",
        "section": "hero",
        "type": "image",
        "content": "/static/images/dandelion_hero.png",
    },
    {
        "key": "hero.trust_1",
        "section": "hero",
        "type": "text",
        "content": "Ganzheitlich-Integrative Atemtherapie (IKP)",
    },
    {
        "key": "hero.trust_2",
        "section": "hero",
        "type": "text",
        "content": "In Gemeinschaftspraxis Physiotherapie",
    },
    {
        "key": "about.title",
        "section": "about",
        "type": "text",
        "content": "PUSTERUM",
    },
    {
        "key": "about.subtitle",
        "section": "about",
        "type": "text",
        "content": "Praxis für Atem- und Körpertherapie • Stephanie",
    },
    {
        "key": "about.meaning_title",
        "section": "about",
        "type": "text",
        "content": "PUSTERUM [ˈpuːsdəʀomʔ]",
    },
    {
        "key": "about.meaning_text",
        "section": "about",
        "type": "textarea",
        "content": (
            "Pusterum ist ein dänisches Wort und bedeutet auf Deutsch „Raum zum Atmen“ oder im"
            " übertragenen Sinne „Atempause“, „Erholungspause“ bzw. „Zufluchtsort“. Setzt man das"
            " Wort wörtlich aus den dänischen Begriffen zusammen, beschreibt es einen Freiraum"
            " oder Moment, in dem man durchatmen und dem Alltagsstress entfliehen kann."
        ),
    },
    {
        "key": "about.bio",
        "section": "about",
        "type": "textarea",
        "content": (
            "Willkommen in meiner Praxis für Atem- und Körpertherapie. Mein Name ist Stephanie."
            " Der Gesundheits- und komplementärtherapeutische Bereich interessierte mich schon"
            " früh."
            " Einerseits lernte ich im Laufe der Jahre unterschiedliche wirksame Therapiemethoden"
            " für verschiedene gesundheitliche Beschwerden kennen. Andererseits absolvierte ich in"
            " diesem Bereich zwei Ausbildungen – als Ernährungscoach und als Yogalehrerin – blieb"
            " jedoch weiterhin meiner kaufmännischen Haupttätigkeit treu."
        ),
    },
    {
        "key": "about.interdisciplinary",
        "section": "about",
        "type": "textarea",
        "content": (
            "Mit der Zeit wuchs in mir der Wunsch nach einer beruflichen Veränderung, die mehr"
            " Sinnhaftigkeit und persönlichen Ausgleich bietet. Den entscheidenden Impuls für diese"
            " Neuausrichtung gab schliesslich eine gesundheitlich herausfordernde Phase. Bei meiner"
            " Suche nach neuen Wegen bin ich auf die Atem- und Körpertherapie gestossen; sie hat"
            " mich"
            " von Anfang an tief begeistert. Der lebensnotwendige Atem ist so selbstverständlich"
            " und"
            " allgegenwärtig und dennoch unbeachtet, wird er jedoch bewusst wahrgenommen ist er"
            " äusserst kraftvoll. Die Arbeit mit dem Atem fasziniert mich durch ihre Direktheit und"
            " ihre ganzheitliche Wirkung auf Körper und Geist. Heute nutze ich die Erfahrungen, die"
            " ich in den bisherigen Jahren meiner Ausbildung sammeln durfte, um Menschen auf ihrem"
            " Weg zu mehr Wohlbefinden, Selbstheilung und innerer Balance kompetent zu begleiten."
        ),
    },
    {
        "key": "about.quote",
        "section": "about",
        "type": "text",
        "content": (
            "«So wie du atmest, so geht es dir. So wie es dir geht, so atmest du.»\n"
            "– Ganzheitlich-Integrative Atemtherapie (IKP)"
        ),
    },
    {
        "key": "about.portrait",
        "section": "about",
        "type": "image",
        "content": "/static/images/stephanie_portrait.jpg",
    },
    {
        "key": "about.badge_title",
        "section": "about",
        "type": "text",
        "content": "Atemtherapie IKP",
    },
    {
        "key": "about.badge_subtitle",
        "section": "about",
        "type": "text",
        "content": "Ganzheitlich-Integrativ",
    },
    {
        "key": "about.credential_1",
        "section": "about",
        "type": "text",
        "content": (
            "2023 – heute: Ausbildung Ganzheitlich integrative Atemtherapie,"
            " IKP Institut für Körperzentrierte Psychotherapie"
        ),
    },
    {
        "key": "about.credential_2",
        "section": "about",
        "type": "text",
        "content": "2014: Diplom Yogalehrerin, International Sivananda Yoga Vedanta Centre",
    },
    {
        "key": "about.credential_3",
        "section": "about",
        "type": "text",
        "content": "2006 – 2007: Diplom ErnährungsCoach, Klubschule Migros",
    },
    {
        "key": "about.credential_4",
        "section": "about",
        "type": "text",
        "content": "In Gemeinschaftspraxis Physiotherapie",
    },
    {
        "key": "competencies.badge",
        "section": "competencies",
        "type": "text",
        "content": "Methode & Wirkung",
    },
    {
        "key": "competencies.title",
        "section": "competencies",
        "type": "text",
        "content": "Was ist Atem- und Körpertherapie?",
    },
    {
        "key": "competencies.subtitle",
        "section": "competencies",
        "type": "textarea",
        "content": "Atem- und Körpertherapie – die Brücke zwischen Körper und Psyche.",
    },
    {
        "key": "competencies.bridge_p1",
        "section": "competencies",
        "type": "textarea",
        "content": (
            "Der Atem begleitet uns durch unser ganzes Leben. Er ist die Verbindung zwischen"
            " Körper und Psyche: Er reagiert auf das, was uns beschäftigt, auf unsere Gefühle, auf"
            " Anspannung, Bewegung und Körperhaltung. Als einzige autonome Körperfunktion lässt"
            " sich"
            " der Atem jedoch auch willentlich aktiv beeinflussen."
        ),
    },
    {
        "key": "competencies.bridge_p2",
        "section": "competencies",
        "type": "textarea",
        "content": (
            "In der Atem- und Körpertherapie nutzen wir diese Verbindung des direkten Zugangs"
            " zur Psyche. Dabei steht die achtsame Selbstwahrnehmung im Mittelpunkt. Es geht nicht"
            " darum, richtig zu atmen oder den Atem bewusst zu steuern, sondern den Atem in seiner"
            " natürlichen Bewegung wahrzunehmen und den eigenen Körper bewusster zu erleben."
        ),
    },
    {
        "key": "competencies.bridge_p3",
        "section": "competencies",
        "type": "textarea",
        "content": (
            "Durch diese sanfte und achtsame Arbeit können körperliche und seelische Spannungen"
            " und Blockaden gelöst und nachhaltig positiv beeinflusst werden. Das begleitende"
            " therapeutische Gespräch unterstützt dabei, die gemachten körperlichen und"
            " persönlichen"
            " Erfahrungen wahrzunehmen, zu reflektieren und besser einzuordnen."
        ),
    },
    {
        "key": "competencies.bridge_p4",
        "section": "competencies",
        "type": "textarea",
        "content": (
            "Diese bewussten Wahrnehmungen von Atem und Körper können helfen, Anspannung"
            " loszulassen, zur Ruhe zu kommen und die eigenen Kräfte und Ressourcen wieder stärker"
            " zu spüren. So können mehr Vertrauen in den eigenen Körper, ein vertieftes"
            " Körpergefühl"
            " und ein bewussterer Umgang mit den Herausforderungen und Belastungen des Alltags"
            " entstehen."
        ),
    },
    {
        "key": "competencies.for_whom_title",
        "section": "competencies",
        "type": "text",
        "content": "Für wen eignet sich Atem- und Körpertherapie?",
    },
    {
        "key": "competencies.for_whom_subtitle",
        "section": "competencies",
        "type": "textarea",
        "content": (
            "Atem- und Körpertherapie wirkt in vielen Bereichen – vor allem nutzt sie den direkten"
            " Zugang zur Psyche. Dabei steht nicht nur der Atem im Mittelpunkt. Atem- und"
            " Körperübungen, Körperbehandlungen auf der Liege und das begleitende Gespräch ergänzen"
            " sich. Die Therapieform kann unter anderem in folgenden Bereichen unterstützen:"
        ),
    },
    {
        "key": "competencies.for_whom_1",
        "section": "competencies",
        "type": "text",
        "content": "Stress, Anspannung und innerer Unruhe",
    },
    {
        "key": "competencies.for_whom_2",
        "section": "competencies",
        "type": "text",
        "content": "Erschöpfung und dem Gefühl, nicht mehr richtig abschalten zu können",
    },
    {
        "key": "competencies.for_whom_3",
        "section": "competencies",
        "type": "text",
        "content": "Verspannungen und körperlichen Beschwerden",
    },
    {
        "key": "competencies.for_whom_4",
        "section": "competencies",
        "type": "text",
        "content": "eingeschränkter oder oberflächlicher Atmung",
    },
    {
        "key": "competencies.for_whom_5",
        "section": "competencies",
        "type": "text",
        "content": "Schlafproblemen",
    },
    {
        "key": "competencies.for_whom_6",
        "section": "competencies",
        "type": "text",
        "content": "Ängsten und emotionalen Belastungen",
    },
    {
        "key": "competencies.for_whom_7",
        "section": "competencies",
        "type": "text",
        "content": "dem Wunsch nach mehr Körperwahrnehmung, Ruhe und innerer Balance",
    },
    {
        "key": "competencies.for_whom_8",
        "section": "competencies",
        "type": "text",
        "content": "als Begleitung in besonderen Lebenssituationen",
    },
    {
        "key": "quotes.1.text",
        "section": "quotes",
        "type": "textarea",
        "content": (
            "«Die Fähigkeit, bewusst zu atmen, ist das Geschenk, das uns hilft,"
            " das Leben voll auszukosten.»"
        ),
    },
    {
        "key": "quotes.1.author",
        "section": "quotes",
        "type": "text",
        "content": "James Nestor",
    },
    {
        "key": "quotes.2.text",
        "section": "quotes",
        "type": "textarea",
        "content": (
            "«Der Atem ist das Werkzeug, mit dem wir die Chemie unseres Körpers verändern können.»"
        ),
    },
    {
        "key": "quotes.2.author",
        "section": "quotes",
        "type": "text",
        "content": "Wim Hof",
    },
    {
        "key": "quotes.3.text",
        "section": "quotes",
        "type": "textarea",
        "content": "«Der Atem ist das Tor zur Gegenwart.»",
    },
    {
        "key": "quotes.3.author",
        "section": "quotes",
        "type": "text",
        "content": "Eckhart Tolle",
    },
    {
        "key": "quotes.4.text",
        "section": "quotes",
        "type": "textarea",
        "content": ("«Durch den Atem können wir die Energie des Lebens selbst kontrollieren.»"),
    },
    {
        "key": "quotes.4.author",
        "section": "quotes",
        "type": "text",
        "content": "Swami Sivananda",
    },
    {
        "key": "quotes.5.text",
        "section": "quotes",
        "type": "textarea",
        "content": (
            "«Atmen ist der einzige Prozess, der sowohl unbewusst als auch bewusst"
            " ablaufen kann – genau hier liegt seine transformierende Kraft.»"
        ),
    },
    {
        "key": "quotes.5.author",
        "section": "quotes",
        "type": "text",
        "content": "Leonard Orr",
    },
    {
        "key": "quotes.6.text",
        "section": "quotes",
        "type": "textarea",
        "content": (
            "«Lachen entspannt den ganzen Körper – eine innere Massage, die mit"
            " einem tiefen Atem beginnt.»"
        ),
    },
    {
        "key": "quotes.6.author",
        "section": "quotes",
        "type": "text",
        "content": "Norman Cousins",
    },
    {
        "key": "services.badge",
        "section": "services",
        "type": "text",
        "content": "Transparente Tarife & Behandlungsablauf",
    },
    {
        "key": "services.title",
        "section": "services",
        "type": "text",
        "content": "Angebote & Behandlungsablauf",
    },
    {
        "key": "services.subtitle",
        "section": "services",
        "type": "textarea",
        "content": (
            "Jede Behandlung wird individuell auf Ihre aktuelle Lebenssituation und Ihre"
            " persönlichen Bedürfnisse abgestimmt."
        ),
    },
    {
        "key": "services.empty_text",
        "section": "services",
        "type": "textarea",
        "content": (
            "Tarife auf Anfrage – gerne beantworte ich Ihre Fragen zu Ablauf und Kosten persönlich."
        ),
    },
    {
        "key": "services.insurance_title",
        "section": "services",
        "type": "text",
        "content": "Therapie & Rahmenbedingungen",
    },
    {
        "key": "services.insurance_text",
        "section": "services",
        "type": "textarea",
        "content": (
            "Als Atem- und Körpertherapeutin in Ausbildung am IKP begleite ich Sie einfühlsam und"
            " fundiert. Behandlungen finden in geschützter Atmosphäre in den Räumen der"
            " Gemeinschaftspraxis Physiotherapie statt."
        ),
    },
    {
        "key": "services.insurance_label_1",
        "section": "services",
        "type": "text",
        "content": "Ganzheitlich integrative Atemtherapie IKP",
    },
    {
        "key": "services.insurance_label_2",
        "section": "services",
        "type": "text",
        "content": "Gemeinschaftspraxis Physiotherapie",
    },
    {
        "key": "kids.badge",
        "section": "kids",
        "type": "text",
        "content": "Für Kinder",
    },
    {
        "key": "kids.title",
        "section": "kids",
        "type": "text",
        "content": "Die atmende Blume",
    },
    {
        "key": "kids.subtitle",
        "section": "kids",
        "type": "textarea",
        "content": (
            "Eine spielerische Atemübung für Ruhe und Konzentration: Die Hände werden zur"
            " Blüte, die sich mit dem Atem öffnet und wieder schliesst – im Stehen oder im"
            " Sitzen."
        ),
    },
    {
        "key": "kids.variant_1.title",
        "section": "kids",
        "type": "text",
        "content": "Die Knospe öffnet sich",
    },
    {
        "key": "kids.variant_1.text",
        "section": "kids",
        "type": "textarea",
        "content": (
            "Lege deine Handflächen vor der Brust aneinander, die Daumen zeigen zu dir."
            " Beim Einatmen gehen nur die Fingerspitzen auseinander – die Handballen bleiben"
            " zusammen. Beim Ausatmen schliesst sich die Knospe wieder."
        ),
    },
    {
        "key": "kids.variant_2.title",
        "section": "kids",
        "type": "text",
        "content": "Die Blüte geht auf",
    },
    {
        "key": "kids.variant_2.text",
        "section": "kids",
        "type": "textarea",
        "content": (
            "Jetzt öffnen sich beim Einatmen deine ganzen Hände nach links und nach rechts."
            " Beim Ausatmen kommen sie vor der Brust wieder zusammen."
        ),
    },
    {
        "key": "kids.variant_3.title",
        "section": "kids",
        "type": "text",
        "content": "Die grosse Blume",
    },
    {
        "key": "kids.variant_3.text",
        "section": "kids",
        "type": "textarea",
        "content": (
            "Beim Einatmen streckst du die Hände nach vorne und öffnest sie weit zur Seite."
            " Beim Ausatmen führst du sie in einem grossen Bogen zurück vor die Brust – fast"
            " wie beim Brustschwimmen."
        ),
    },
    {
        "key": "kids.variant_4.title",
        "section": "kids",
        "type": "text",
        "content": "Die Blumenwiese (in der Gruppe)",
    },
    {
        "key": "kids.variant_4.text",
        "section": "kids",
        "type": "textarea",
        "content": (
            "Ihr sitzt im Kreis und haltet euch an den Händen. Beim Einatmen hebt ihr die"
            " Hände gemeinsam hoch über den Kopf, beim Ausatmen lasst ihr sie langsam wieder"
            " sinken."
        ),
    },
    {
        "key": "kids.variant_1.photo_closed",
        "section": "kids",
        "type": "image",
        # Optional real photo of the exercise, uploaded by the practice owner (empty = none)
        "content": "",
    },
    {
        "key": "kids.variant_1.photo_open",
        "section": "kids",
        "type": "image",
        # Optional real photo of the exercise, uploaded by the practice owner (empty = none)
        "content": "",
    },
    {
        "key": "kids.variant_2.photo_closed",
        "section": "kids",
        "type": "image",
        # Optional real photo of the exercise, uploaded by the practice owner (empty = none)
        "content": "",
    },
    {
        "key": "kids.variant_2.photo_open",
        "section": "kids",
        "type": "image",
        # Optional real photo of the exercise, uploaded by the practice owner (empty = none)
        "content": "",
    },
    {
        "key": "kids.variant_3.photo_closed",
        "section": "kids",
        "type": "image",
        # Optional real photo of the exercise, uploaded by the practice owner (empty = none)
        "content": "",
    },
    {
        "key": "kids.variant_3.photo_open",
        "section": "kids",
        "type": "image",
        # Optional real photo of the exercise, uploaded by the practice owner (empty = none)
        "content": "",
    },
    {
        "key": "kids.variant_4.photo_closed",
        "section": "kids",
        "type": "image",
        # Optional real photo of the exercise, uploaded by the practice owner (empty = none)
        "content": "",
    },
    {
        "key": "kids.variant_4.photo_open",
        "section": "kids",
        "type": "image",
        # Optional real photo of the exercise, uploaded by the practice owner (empty = none)
        "content": "",
    },
    {
        "key": "kids.player_hint",
        "section": "kids",
        "type": "textarea",
        "content": (
            "Probiere es gleich aus: Die Blume zeigt dir den Rhythmus. Zum Schluss darfst"
            " du die Pusteblume auspusten."
        ),
    },
    {
        "key": "kids.tips_title",
        "section": "kids",
        "type": "text",
        "content": "Gut zu wissen",
    },
    {
        "key": "kids.tips",
        "section": "kids",
        "type": "rich_text",
        "content": (
            "- **Mit Freude:** spielerisch und mit Bildern üben – nichts muss perfekt sein.\n"
            "- **Ohne Anstrengung:** Die Bewegung folgt immer dem eigenen Atem.\n"
            "- **Ankommen:** Vorher ein paar Atemzüge lang spüren, wie der Atem kommt und geht.\n"
            "- **Nachspüren:** Danach die Hände sinken lassen und noch kurz dem Atem lauschen.\n"
            "- **Als Ritual:** Am schönsten jeden Tag zur gleichen Zeit, z. B. vor dem Einschlafen."
        ),
    },
    {
        "key": "kids.source",
        "section": "kids",
        "type": "text",
        "content": "Nach einer Übungsidee aus dem Kinderyoga von Volker Friebel.",
    },
    {
        "key": "practice.name",
        "section": "practice",
        "type": "text",
        "content": "PUSTERUM",
    },
    {
        "key": "practice.setting",
        "section": "practice",
        "type": "text",
        "content": "Gemeinschaftspraxis • Raum für Ruhe & Ankommen",
    },
    {
        "key": "practice.title",
        "section": "practice",
        "type": "text",
        "content": "Die Praxisräume",
    },
    {
        "key": "practice.description",
        "section": "practice",
        "type": "textarea",
        "content": (
            "Die Praxis PUSTERUM für Atem- und Körpertherapie ist eingebettet in eine modern"
            " ausgestattete Physiotherapie-Gemeinschaftspraxis. Ein geschützter, ruhiger Raum mit"
            " angenehmer Atmosphäre lädt dazu ein, den Alltag hinter sich zu lassen und ganz bei"
            " sich und dem eigenen Atem anzukommen."
        ),
    },
    {
        "key": "practice.address",
        "section": "practice",
        "type": "text",
        "content": "Beispielweg 0, 3000 Bern",
    },
    {
        "key": "practice.phone",
        "section": "practice",
        "type": "phone",
        "content": "+41 31 000 00 00",
    },
    {
        "key": "practice.email",
        "section": "practice",
        "type": "email",
        "content": "info@pusterum.be",
    },
    {
        "key": "practice.location_name",
        "section": "practice",
        "type": "text",
        "content": "Physio La Fontaine",
    },
    {
        "key": "practice.location_address",
        "section": "practice",
        "type": "text",
        "content": "Rüschlistrasse 9, 2502 Biel",
    },
    {
        "key": "practice.location_website",
        "section": "practice",
        "type": "text",
        "content": "physio-lafontaine.ch",
    },
    {
        "key": "practice.directions",
        "section": "practice",
        "type": "rich_text",
        # Markup: **fett**, *kursiv*, __unterstrichen__, "- " Liste (presentation/rich_text.py)
        "content": (
            "**Anreise mit dem ÖV ab Bahnhof Biel**\n"
            "Die Anreise vom Hauptbahnhof Biel/Bienne dauert nur ca. 5 bis 7 Minuten.\n\n"
            "- **Bus nehmen:** Am Bahnhofplatz Biel in den Bus (Linie 1, 5, 6 oder 8) Richtung"
            " Innenstadt / Altstadt einsteigen.\n"
            "- **Aussteigen:** An der Haltestelle Biel/Bienne, Altstadt (Vieille Ville) oder"
            " Zentralplatz aussteigen.\n"
            "- **Fussweg (ca. 2 Minuten):** Von der Haltestelle sind es nur wenige Schritte in die"
            " Rüschlistrasse 9.\n\n"
            "*Alternativ ist die Praxis vom Bahnhof aus auch zu Fuss in ca. 10 bis 12 Minuten"
            " bequem erreichbar.*"
        ),
    },
    {
        "key": "practice.accessibility",
        "section": "practice",
        "type": "textarea",
        "content": "",
    },
    {
        "key": "practice.interior_image",
        "section": "practice",
        "type": "image",
        "content": "/static/images/practice_interior.png",
    },
    {
        "key": "contact.badge",
        "section": "contact",
        "type": "text",
        "content": "Verbindung aufnehmen",
    },
    {
        "key": "contact.title",
        "section": "contact",
        "type": "text",
        "content": "Kontakt & Terminanfrage",
    },
    {
        "key": "contact.subtitle",
        "section": "contact",
        "type": "textarea",
        "content": (
            "Haben Sie Fragen zur Atem- und Körpertherapie oder möchten Sie einen Termin"
            " vereinbaren? Ich freue mich auf Ihre Nachricht oder Ihren Anruf."
        ),
    },
    {
        "key": "contact.phone_label",
        "section": "contact",
        "type": "text",
        "content": "Telefonische Erreichbarkeit",
    },
    {
        "key": "contact.email_label",
        "section": "contact",
        "type": "text",
        "content": "E-Mail",
    },
    {
        "key": "contact.privacy_note",
        "section": "contact",
        "type": "textarea",
        "content": (
            "Ihre Angaben werden vertraulich behandelt und ausschliesslich zur Beantwortung Ihrer "
            "Anfrage genutzt. Details finden Sie in der Datenschutzerklärung."
        ),
    },
    {
        "key": "impressum.title",
        "section": "impressum",
        "type": "text",
        "content": "Impressum",
    },
    {
        "key": "impressum.responsible_title",
        "section": "impressum",
        "type": "text",
        "content": "Verantwortliche Stelle",
    },
    {
        "key": "impressum.owner_name",
        "section": "impressum",
        "type": "text",
        "content": "Stephanie",
    },
    {
        "key": "impressum.recognition_title",
        "section": "impressum",
        "type": "text",
        "content": "Ausbildung & Methode",
    },
    {
        "key": "impressum.recognition_text",
        "section": "impressum",
        "type": "textarea",
        "content": (
            "PUSTERUM – Praxis für Atem- und Körpertherapie\nStephanie\n"
            "Ausbildung Ganzheitlich integrative Atemtherapie, IKP Institut für Körperzentrierte"
            " Psychotherapie\n"
            "Eingebettet in Physiotherapie-Gemeinschaftspraxis."
        ),
    },
    {
        "key": "impressum.disclaimer_title",
        "section": "impressum",
        "type": "text",
        "content": "Haftungsausschluss",
    },
    {
        "key": "impressum.disclaimer_text",
        "section": "impressum",
        "type": "textarea",
        "content": (
            "Die Inhalte dieser Webseite wurden mit grösstmöglicher Sorgfalt erstellt. Für die"
            " Richtigkeit, Vollständigkeit und Aktualität der Inhalte übernimmt die"
            " Praxisinhaberin keine Gewähr. Die bereitgestellten Informationen stellen keine"
            " medizinische Diagnose dar und ersetzen nicht die Konsultation einer Ärztin oder"
            " eines Arztes."
        ),
    },
    {
        "key": "datenschutz.title",
        "section": "datenschutz",
        "type": "text",
        "content": "Datenschutzerklärung",
    },
    {
        "key": "datenschutz.intro",
        "section": "datenschutz",
        "type": "textarea",
        "content": (
            "Der Schutz Ihrer persönlichen Daten ist mir ein wichtiges Anliegen. Diese"
            " Datenschutzerklärung informiert Sie über die Erhebung und Bearbeitung"
            " personenbezogener Daten beim Besuch dieser Website und bei der Kontaktaufnahme"
            " gemäss dem Schweizerischen Datenschutzgesetz (DSG)."
        ),
    },
    {
        "key": "datenschutz.sec1_title",
        "section": "datenschutz",
        "type": "text",
        "content": "1. Verantwortliche Person",
    },
    {
        "key": "datenschutz.sec1_text",
        "section": "datenschutz",
        "type": "textarea",
        "content": (
            "Verantwortlich für die Datenbearbeitung auf dieser Webseite ist die"
            " Praxisinhaberin gemäss Angaben im Impressum."
        ),
    },
    {
        "key": "datenschutz.sec2_title",
        "section": "datenschutz",
        "type": "text",
        "content": "2. Kontaktformular und E-Mail",
    },
    {
        "key": "datenschutz.sec2_text",
        "section": "datenschutz",
        "type": "textarea",
        "content": (
            "Wenn Sie das Kontaktformular nutzen oder mir eine E-Mail senden, bearbeite ich Ihre "
            "Angaben (Name, E-Mail-Adresse, optional Telefonnummer, Betreff und Nachricht) "
            "ausschliesslich, um Ihre Anfrage zu beantworten. Zum Schutz vor Missbrauch wird "
            "zusätzlich die IP-Adresse gespeichert. Sie erhalten eine kurze automatische "
            "Empfangsbestätigung per E-Mail. Kontaktanfragen werden nach spätestens 12 Monaten "
            "automatisch gelöscht. Ihre Daten werden nicht an Dritte weitergegeben – ausgenommen "
            "die technischen Dienstleister für Hosting und E-Mail-Versand, die sie ausschliesslich "
            "in meinem Auftrag bearbeiten."
        ),
    },
    {
        "key": "datenschutz.sec3_title",
        "section": "datenschutz",
        "type": "text",
        "content": "3. Hosting und Server-Logfiles",
    },
    {
        "key": "datenschutz.sec3_text",
        "section": "datenschutz",
        "type": "textarea",
        "content": (
            "Diese Website wird bei einer Hosting-Anbieterin in Rechenzentren in Deutschland bzw. "
            "Finnland (EU) betrieben; für die EU besteht gemäss DSG ein angemessenes "
            "Datenschutzniveau. Beim Aufruf der Website werden technisch notwendige Angaben "
            "(IP-Adresse, Datum und Uhrzeit, aufgerufene Seite, Browsertyp) in Server-Logfiles "
            "erfasst. Sie dienen ausschliesslich der Sicherheit und Fehleranalyse und werden "
            "regelmässig gelöscht."
        ),
    },
    {
        "key": "datenschutz.sec4_title",
        "section": "datenschutz",
        "type": "text",
        "content": "4. Schutz vor Spam und Missbrauch",
    },
    {
        "key": "datenschutz.sec4_text",
        "section": "datenschutz",
        "type": "textarea",
        "content": (
            "Das Kontaktformular ist mit ALTCHA geschützt – einer Sicherheitsprüfung, die "
            "vollständig auf diesem Server läuft. Ihr Browser löst dabei eine kleine "
            "Rechenaufgabe; es werden keine Cookies gesetzt und keine Daten an Dritte übermittelt."
        ),
    },
    {
        "key": "datenschutz.sec5_title",
        "section": "datenschutz",
        "type": "text",
        "content": "5. Cookies und Schriftarten",
    },
    {
        "key": "datenschutz.sec5_text",
        "section": "datenschutz",
        "type": "textarea",
        "content": (
            "Diese Website verwendet keine Analyse- oder Tracking-Dienste und keine Werbe-Cookies. "
            "Gesetzt werden ausschliesslich technisch notwendige Cookies: ein Sicherheits-Cookie "
            "zum Schutz der Formulare vor Missbrauch (CSRF-Schutz) sowie – nur für die "
            "Praxisinhaberin – ein Anmelde-Cookie für den Verwaltungsbereich. Alle Schriftarten "
            "werden direkt von diesem Server geladen; es besteht keine Verbindung zu Google oder "
            "anderen Drittanbietern."
        ),
    },
    {
        "key": "datenschutz.sec6_title",
        "section": "datenschutz",
        "type": "text",
        "content": "6. Ihre Rechte",
    },
    {
        "key": "datenschutz.sec6_text",
        "section": "datenschutz",
        "type": "textarea",
        "content": (
            "Sie haben jederzeit das Recht auf unentgeltliche Auskunft über Ihre bei mir "
            "gespeicherten Personendaten sowie auf deren Berichtigung oder Löschung. Wenden Sie "
            "sich dazu an die im Impressum genannte E-Mail-Adresse. Zudem können Sie sich beim "
            "Eidgenössischen Datenschutz- und Öffentlichkeitsbeauftragten (EDÖB) beschweren."
        ),
    },
    {
        "key": "footer.tagline",
        "section": "footer",
        "type": "textarea",
        "content": (
            "PUSTERUM – Praxis für Atem- und Körpertherapie. Stephanie.\n"
            "Ausbildung Ganzheitlich integrative Atemtherapie (IKP).\n"
            "Eingebettet in eine interdisziplinäre Physiotherapie-Gemeinschaftspraxis."
        ),
    },
    {
        "key": "impressum.webdesign_title",
        "section": "impressum",
        "type": "text",
        "content": "Konzeption & Webdesign",
    },
    {
        "key": "impressum.webdesign_by",
        "section": "impressum",
        "type": "text",
        "content": "Webdesign bynico.",
    },
    {
        "key": "impressum.webdesign_notice",
        "section": "impressum",
        "type": "text",
        "content": "«bynico.» ist eine eingetragene Marke von Nicolas Mischler.",
    },
    {
        "key": "footer.webdesign",
        "section": "footer",
        "type": "text",
        "content": "Webdesign bynico.",
    },
    {
        "key": "footer.trademark_notice",
        "section": "footer",
        "type": "text",
        "content": "«bynico.» ist eine eingetragene Marke von Nicolas Mischler.",
    },
]


@cache
def content_default_map() -> dict[str, str]:
    """``{key: default content}`` for template fallbacks."""
    return {block["key"]: block["content"] for block in DEFAULT_CONTENT_BLOCKS}


def content_default(key: str) -> str:
    """Default text of a content block (empty string for unknown keys)."""
    return content_default_map().get(key, "")


def count_numbered_keys(prefix: str, suffix: str = "") -> int:
    """Number of keys ``<prefix><n><suffix>`` (n = 1, 2, …), e.g. quotes or list items."""
    count = 0
    while f"{prefix}{count + 1}{suffix}" in content_default_map():
        count += 1
    return count
