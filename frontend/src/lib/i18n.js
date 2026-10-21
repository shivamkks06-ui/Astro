import { useEffect, useState } from "react";

const KEY = "nv:lang";

const HI = {
  // planets & chart
  Sun: "सूर्य", Moon: "चंद्र", Mars: "मंगल", Mercury: "बुध", Jupiter: "गुरु", Venus: "शुक्र", Saturn: "शनि", Rahu: "राहु", Ketu: "केतु", Ascendant: "लग्न",
  Su: "सू", Mo: "चं", Ma: "मं", Me: "बु", Ju: "गु", Ve: "शु", Sa: "श", Ra: "रा", Ke: "के", Asc: "लग्न", "(R)": "(व)",
  Aries: "मेष", Taurus: "वृषभ", Gemini: "मिथुन", Cancer: "कर्क", Leo: "सिंह", Virgo: "कन्या", Libra: "तुला", Scorpio: "वृश्चिक",
  Sagittarius: "धनु", Capricorn: "मकर", Aquarius: "कुंभ", Pisces: "मीन",
  Mesha: "मेष", Vrishabha: "वृषभ", Mithuna: "मिथुन", Karka: "कर्क", Simha: "सिंह", Kanya: "कन्या", Tula: "तुला", Vrishchika: "वृश्चिक",
  Dhanu: "धनु", Makara: "मकर", Kumbha: "कुंभ", Meena: "मीन",
  Ashwini: "अश्विनी", Bharani: "भरणी", Krittika: "कृत्तिका", Rohini: "रोहिणी", Mrigashira: "मृगशिरा", Ardra: "आर्द्रा", Punarvasu: "पुनर्वसु",
  Pushya: "पुष्य", Ashlesha: "आश्लेषा", Magha: "मघा", "Purva Phalguni": "पूर्वा फाल्गुनी", "Uttara Phalguni": "उत्तरा फाल्गुनी", Hasta: "हस्त",
  Chitra: "चित्रा", Swati: "स्वाति", Vishakha: "विशाखा", Anuradha: "अनुराधा", Jyeshtha: "ज्येष्ठा", Mula: "मूल", "Purva Ashadha": "पूर्वाषाढ़ा",
  "Uttara Ashadha": "उत्तराषाढ़ा", Shravana: "श्रवण", Dhanishta: "धनिष्ठा", Shatabhisha: "शतभिषा", "Purva Bhadrapada": "पूर्वा भाद्रपद",
  "Uttara Bhadrapada": "उत्तरा भाद्रपद", Revati: "रेवती",
  // panchang
  Pratipada: "प्रतिपदा", Dwitiya: "द्वितीया", Tritiya: "तृतीया", Chaturthi: "चतुर्थी", Panchami: "पंचमी", Shashthi: "षष्ठी", Saptami: "सप्तमी",
  Ashtami: "अष्टमी", Navami: "नवमी", Dashami: "दशमी", Ekadashi: "एकादशी", Dwadashi: "द्वादशी", Trayodashi: "त्रयोदशी", Chaturdashi: "चतुर्दशी",
  Purnima: "पूर्णिमा", Amavasya: "अमावस्या", Shukla: "शुक्ल", Krishna: "कृष्ण",
  "Somavara (Monday)": "सोमवार", "Mangalavara (Tuesday)": "मंगलवार", "Budhavara (Wednesday)": "बुधवार", "Guruvara (Thursday)": "गुरुवार",
  "Shukravara (Friday)": "शुक्रवार", "Shanivara (Saturday)": "शनिवार", "Ravivara (Sunday)": "रविवार",
  Vishkambha: "विष्कम्भ", Priti: "प्रीति", Ayushman: "आयुष्मान", Saubhagya: "सौभाग्य", Shobhana: "शोभन", Atiganda: "अतिगण्ड", Sukarma: "सुकर्मा",
  Dhriti: "धृति", Shula: "शूल", Ganda: "गण्ड", Vriddhi: "वृद्धि", Dhruva: "ध्रुव", Vyaghata: "व्याघात", Harshana: "हर्षण", Vajra: "वज्र",
  Siddhi: "सिद्धि", Vyatipata: "व्यतीपात", Variyana: "वरीयान", Parigha: "परिघ", Shiva: "शिव", Siddha: "सिद्ध", Sadhya: "साध्य", Shubha: "शुभ",
  Brahma: "ब्रह्म", Indra: "इन्द्र", Vaidhriti: "वैधृति",
  Bava: "बव", Balava: "बालव", Kaulava: "कौलव", Taitila: "तैतिल", Garaja: "गर", Vanija: "वणिज", Vishti: "विष्टि", Kimstughna: "किंस्तुघ्न",
  Shakuni: "शकुनि", Chatushpada: "चतुष्पद", Naga: "नाग",
  // matching
  Varna: "वर्ण", Vashya: "वश्य", Tara: "तारा", Yoni: "योनि", "Graha Maitri": "ग्रह मैत्री", Gana: "गण", Bhakoot: "भकूट", Nadi: "नाड़ी",
  Manava: "मानव", Jalachara: "जलचर", Vanachara: "वनचर", Keeta: "कीट",
  Horse: "अश्व", Elephant: "गज", Sheep: "मेढ़ा", Serpent: "सर्प", Dog: "श्वान", Cat: "मार्जार", Rat: "मूषक", Cow: "गौ", Buffalo: "महिष",
  Tiger: "व्याघ्र", Deer: "मृग", Monkey: "वानर", Mongoose: "नकुल", Lion: "सिंह",
  Deva: "देव", Manushya: "मनुष्य", Rakshasa: "राक्षस", Adi: "आदि", Madhya: "मध्य", Antya: "अन्त्य",
  "Temperament and work ethic": "स्वभाव और कार्यशैली", "Birth-star compatibility": "जन्म नक्षत्र अनुकूलता",
  Excellent: "उत्तम", Good: "अच्छा", Average: "मध्यम", Low: "कम", "{band} agreement": "{band} मिलान",
  "Ashtakoota Guna Milan": "अष्टकूट गुण मिलान", "New match": "नया मिलान", "Koota": "कूट", "(boy / girl)": "(वर / वधू)", Score: "अंक",
  Boy: "वर", Girl: "वधू", "Kundli matching": "कुंडली मिलान", "36 Guna Milan": "36 गुण मिलान",
  "Enter both birth details. Traditional Ashtakoota uses the boy's and the girl's roles.": "दोनों का जन्म विवरण भरें। पारंपरिक अष्टकूट में वर और वधू की भूमिका मानी जाती है।",
  "Step 1 of 2: Boy's details": "चरण 1/2: वर का विवरण", "Step 2 of 2: Girl's details": "चरण 2/2: वधू का विवरण",
  "Edit boy's details": "वर का विवरण बदलें", "Check match": "मिलान देखें", "Next: girl's details": "आगे: वधू का विवरण",
  "Traditional doshas present": "पारंपरिक दोष", "Nadi dosha": "नाड़ी दोष", "Bhakoot dosha": "भकूट दोष",
  "Astrologers often check further rules before reading these.": "ज्योतिषी इन्हें पढ़ने से पहले अन्य नियम भी देखते हैं।",
  "Guna Milan is a traditional compatibility score calculated from both Moon positions. It is guidance, not a prediction about any marriage.": "गुण मिलान दोनों की चंद्र स्थिति से निकाला गया पारंपरिक अंक है। यह मार्गदर्शन है, किसी विवाह की भविष्यवाणी नहीं।",
  "For a full reading,": "पूरी जानकारी के लिए", "consult a verified astrologer": "सत्यापित ज्योतिषी से परामर्श करें",
  // manglik
  "Manglik check": "मांगलिक जाँच", "Not Manglik": "मांगलिक नहीं", Manglik: "मांगलिक", "Manglik, traditionally cancelled": "मांगलिक, पारंपरिक रूप से निरस्त",
  "Mars is in its own sign": "मंगल अपनी राशि में है", "Mars is exalted": "मंगल उच्च का है", Cancellation: "निरस्ति",
  "Mars is in house {a} from the Lagna ({x}) and house {b} from the Moon ({y}).": "मंगल लग्न से भाव {a} में ({x}) और चंद्र से भाव {b} में ({y}) है।",
  counts: "गिना जाता है", "does not count": "नहीं गिना जाता",
  "Traditional rule: Mars in house 1, 2, 4, 7, 8 or 12 counted from the Lagna or the Moon.": "पारंपरिक नियम: लग्न या चंद्र से 1, 2, 4, 7, 8 या 12वें भाव में मंगल।",
  "Manglik status is a traditional indicator only. It does not decide whether a marriage will work.": "मांगलिक स्थिति केवल पारंपरिक संकेत है। इससे विवाह की सफलता तय नहीं होती।",
  // panchang
  "Panchang at birth": "जन्म का पंचांग", Tithi: "तिथि", Vara: "वार", Nakshatra: "नक्षत्र", Yoga: "योग", Karana: "करण", Sunrise: "सूर्योदय",
  "Vedic day starts at sunrise; births before sunrise take the previous weekday.": "वैदिक दिन सूर्योदय से शुरू होता है; सूर्योदय से पहले का जन्म पिछले वार में गिना जाता है।",
  // kundli
  "Free Kundli": "निःशुल्क कुंडली", "Your Vedic birth chart": "आपकी वैदिक जन्म कुंडली",
  "Sidereal positions calculated from NASA JPL ephemeris data, with Lagna, houses, nakshatras and Vimshottari dasha.": "NASA JPL एफेमेरिस से गणना की गई निरयण स्थितियाँ: लग्न, भाव, नक्षत्र और विंशोत्तरी दशा।",
  "Kundli matching (36 Guna Milan)": "कुंडली मिलान (36 गुण)", "Calculated chart": "गणना की गई कुंडली", "Birth chart": "जन्म कुंडली",
  "Detailed Kundli report": "विस्तृत कुंडली रिपोर्ट", "Your full report": "आपकी पूरी रिपोर्ट", "Read full report": "पूरी रिपोर्ट पढ़ें", "Show summary only": "केवल सारांश दिखाएँ",
  "Personalized overview": "व्यक्तिगत सारांश", "Birth details and calculation settings": "जन्म विवरण और गणना सेटिंग", "Lagna, Rashi and Nakshatra": "लग्न, राशि और नक्षत्र",
  "Birth charts": "जन्म कुंडलियाँ", "Planetary placements": "ग्रह स्थिति", "Twelve houses (Bhavas)": "बारह भाव", "Important yogas and doshas": "प्रमुख योग और दोष",
  "Career and profession": "करियर और व्यवसाय", "Finance and wealth": "धन और वित्त", "Marriage and relationships": "विवाह और संबंध", "Education and personal growth": "शिक्षा और व्यक्तिगत विकास",
  "Family, home and general well-being": "परिवार, घर और सामान्य कल्याण", "Current and upcoming dasha periods": "वर्तमान और आगामी दशाएँ", "Personalized traditional remedies": "व्यक्तिगत पारंपरिक उपाय",
  "Practical action plan": "व्यावहारिक कार्य योजना", "Disclaimer and calculation limitations": "अस्वीकरण और गणना की सीमाएँ", "Calculated": "गणना", "Traditional interpretation": "पारंपरिक व्याख्या",
  "Depends on birth time": "जन्म समय पर निर्भर", "Not available": "उपलब्ध नहीं", "Premium, coming soon": "प्रीमियम, जल्द आ रहा है", "Get AI interpretation": "AI व्याख्या प्राप्त करें",
  "Writing AI interpretation (up to a minute)": "AI व्याख्या लिखी जा रही है (एक मिनट तक)", "Save this chart to request an optional AI interpretation written from these calculations.": "इन गणनाओं से वैकल्पिक AI व्याख्या पाने के लिए यह कुंडली सहेजें।",
  "Birth time is unknown, so the chart uses 12:00 noon. Sections marked 'Depends on birth time' may be inaccurate.": "जन्म समय अज्ञात है, इसलिए कुंडली दोपहर 12:00 पर बनी है। 'जन्म समय पर निर्भर' वाले भाग गलत हो सकते हैं।",
  "I don't know my exact birth time": "मुझे सही जन्म समय नहीं पता", "The chart will use 12:00 noon. Lagna, houses and dasha dates may be inaccurate.": "कुंडली दोपहर 12:00 पर बनेगी। लग्न, भाव और दशा की तिथियाँ गलत हो सकती हैं।",
  "New chart": "नई कुंडली", Save: "सहेजें", Saved: "सहेजी गई", "Log in to save": "सहेजने के लिए लॉग इन करें", Share: "शेयर", "Print / PDF": "प्रिंट / PDF",
  "Ascendant (Lagna)": "लग्न", "Moon sign (Rashi)": "चंद्र राशि", "Janma nakshatra": "जन्म नक्षत्र", "Current dasha": "वर्तमान दशा", pada: "पद",
  "Rashi (D1)": "राशि (D1)", "Navamsa (D9)": "नवांश (D9)", "North Indian": "उत्तर भारतीय", "South Indian": "दक्षिण भारतीय", RASHI: "राशि", NAVAMSA: "नवांश",
  "Numbers are sign numbers (1 = Aries); house 1 is the top diamond.": "अंक राशि संख्या हैं (1 = मेष); पहला भाव ऊपर का हीरा है।",
  "Signs are fixed; Asc marks the Lagna.": "राशियाँ स्थिर हैं; लग्न चिह्नित है।", "(R) = retrograde.": "(व) = वक्री।",
  "The table below shows Rashi (D1) positions.": "नीचे की तालिका राशि (D1) स्थिति दिखाती है।",
  Planet: "ग्रह", Sign: "राशि", Degree: "अंश", House: "भाव", Pada: "पद",
  "Vimshottari dasha": "विंशोत्तरी दशा", "Balance at birth": "जन्म के समय शेष", yrs: "वर्ष", "Now running": "अभी चल रही", mahadasha: "महादशा",
  "(current)": "(वर्तमान)", "All mahadashas": "सभी महादशाएँ", "No running period in the calculated 120-year cycle.": "120 वर्ष के चक्र में कोई चालू दशा नहीं।",
  Method: "पद्धति", "Saved charts": "सहेजी गई कुंडलियाँ",
  "These are astronomical calculations; any reading of them is interpretive guidance, not a prediction.": "ये खगोलीय गणनाएँ हैं; इनका कोई भी फल मार्गदर्शन है, भविष्यवाणी नहीं।",
  // form
  Name: "नाम", "(optional)": "(वैकल्पिक)", "Date of birth": "जन्म तिथि", "Time of birth (local)": "जन्म समय (स्थानीय)", "Place of birth": "जन्म स्थान",
  "Calculate Kundli": "कुंडली बनाएँ", "Start typing a city, e.g. Varanasi": "शहर लिखें, जैसे वाराणसी", "Search worldwide (OpenStreetMap)": "दुनिया भर में खोजें (OpenStreetMap)",
  "Enter the birth date and time.": "जन्म तिथि और समय भरें।", "Birth year must be between 1900 and 2049.": "जन्म वर्ष 1900 से 2049 के बीच होना चाहिए।", "Choose the birthplace from the list.": "सूची से जन्म स्थान चुनें।",
  "Your birth details are used only to calculate the chart. They are stored only if you save the chart to your account.": "आपका जन्म विवरण केवल कुंडली बनाने में उपयोग होता है। कुंडली सहेजने पर ही यह आपके खाते में रखा जाता है।",
  // horoscope
  "Daily horoscope": "दैनिक राशिफल", "Today under the stars": "आज का राशिफल", "Yesterday under the stars": "बीते कल का राशिफल", "Tomorrow under the stars": "आने वाले कल का राशिफल",
  "Pick your Moon sign (Rashi). Readings come from the day's real sidereal planet positions.": "अपनी चंद्र राशि चुनें। फल उस दिन की वास्तविक निरयण ग्रह स्थिति से निकाला गया है।",
  yesterday: "बीता कल", today: "आज", tomorrow: "आने वाला कल", Favourable: "शुभ", Mixed: "मिश्रित", "Take care": "सावधानी",
  Career: "करियर", Relationships: "संबंध", Health: "स्वास्थ्य", Finance: "धन", Why: "क्यों",
  "AI interpretation": "AI व्याख्या", "Calculated reading": "गणना आधारित फल", "Planet positions used": "प्रयुक्त ग्रह स्थिति",
  "AI interpretation is shown in English.": "AI व्याख्या अंग्रेज़ी में दिखाई जाती है।",
  "AI interpretation is being written. The calculated reading is shown meanwhile.": "AI व्याख्या लिखी जा रही है। तब तक गणना आधारित फल देखें।",
  "AI interpretation is unavailable right now; showing the calculated reading.": "AI व्याख्या अभी उपलब्ध नहीं; गणना आधारित फल दिखाया गया है।",
  "The Moon is in house {n} from your sign.": "चंद्र आपकी राशि से भाव {n} में है।", "{p} in house {n} from {s}": "{s} से भाव {n} में {p}",
  ".": "।", "Reading the transits": "गोचर पढ़ा जा रहा है", "No city in the offline list.": "ऑफ़लाइन सूची में यह शहर नहीं है।",
  "Loading saved charts": "सहेजी गई कुंडलियाँ लोड हो रही हैं", "Calculating chart": "कुंडली की गणना हो रही है", "No saved charts yet": "अभी कोई कुंडली सहेजी नहीं गई",
  "Calculate a Kundli and tap Save to keep it here.": "कुंडली बनाएँ और यहाँ रखने के लिए सहेजें दबाएँ।",
  "Sidereal zodiac, Lahiri ayanamsa ({a}°), Whole sign houses, Mean node, JPL DE421 ephemeris.": "निरयण राशिचक्र, लाहिरी अयनांश ({a}°), संपूर्ण राशि भाव, मध्यम राहु-केतु, JPL DE421 एफेमेरिस।",
  "Horoscopes are general guidance for everyone sharing a Moon sign, not personal predictions. For decisions about health, money or relationships, consult a qualified professional.": "राशिफल एक ही चंद्र राशि वाले सभी लोगों के लिए सामान्य मार्गदर्शन है, व्यक्तिगत भविष्यवाणी नहीं। स्वास्थ्य, धन या संबंधों के निर्णय के लिए योग्य विशेषज्ञ से सलाह लें।",
  "Sidereal (Lahiri) transits at 06:00 IST, counted from your Moon sign (Chandra gochar).": "प्रातः 06:00 IST की निरयण (लाहिरी) गोचर स्थिति, आपकी चंद्र राशि से गिनी गई (चंद्र गोचर)।",
  "Work matters move with less friction; a good day to present ideas or finish pending tasks.": "काम में रुकावटें कम रहेंगी; विचार रखने या अधूरे काम पूरे करने का अच्छा दिन।",
  "Steady effort pays more than bold moves today; double-check details before committing.": "आज साहसिक कदमों से ज़्यादा लगातार मेहनत काम आएगी; निर्णय से पहले विवरण दोबारा जाँचें।",
  "Keep a low profile at work and avoid hasty decisions; review rather than launch.": "काम पर संयम रखें और जल्दबाज़ी के निर्णय से बचें; नया शुरू करने के बजाय समीक्षा करें।",
  "Warm, easy energy for conversations with partners, family and friends.": "जीवनसाथी, परिवार और मित्रों से बातचीत के लिए सहज, स्नेहपूर्ण समय।",
  "Listen more than you speak; small misunderstandings clear up with patience.": "बोलने से ज़्यादा सुनें; छोटी गलतफ़हमियाँ धैर्य से दूर होंगी।",
  "Give people space and avoid reacting to passing moods, including your own.": "दूसरों को समय दें और क्षणिक मनोदशा पर प्रतिक्रिया से बचें, अपनी भी।",
  "Energy levels feel supportive; a good day for routine exercise and rest in balance.": "ऊर्जा अनुकूल है; नियमित व्यायाम और संतुलित आराम का अच्छा दिन।",
  "Pace yourself and keep regular meals and sleep.": "अपनी गति संतुलित रखें, भोजन और नींद नियमित रखें।",
  "Avoid overexertion and rest when you need to. See a doctor for any health concern.": "अधिक थकान से बचें और ज़रूरत पर आराम करें। स्वास्थ्य संबंधी किसी भी चिंता के लिए डॉक्टर से मिलें।",
  "A sensible day to review budgets or plan savings.": "बजट की समीक्षा या बचत की योजना के लिए उपयुक्त दिन।",
  "Keep spending to plan and postpone non-essential purchases.": "खर्च योजना के अनुसार रखें और ग़ैर-ज़रूरी ख़रीदारी टालें।",
  "Avoid impulsive spending or risky commitments today. This is not financial advice.": "आज आवेग में ख़र्च या जोखिम भरे वादों से बचें। यह वित्तीय सलाह नहीं है।",
  "The Moon transits a supportive house from your sign, so the day's tone is generally encouraging.": "चंद्र आपकी राशि से अनुकूल भाव में है, इसलिए दिन सामान्यतः उत्साहजनक रहेगा।",
  "A balanced day: some support, some friction. Keep plans flexible.": "संतुलित दिन: कुछ सहयोग, कुछ रुकावट। योजनाएँ लचीली रखें।",
  "The Moon transits a sensitive house from your sign; go gently and avoid rushing.": "चंद्र आपकी राशि से संवेदनशील भाव में है; धीरे चलें और जल्दबाज़ी न करें।",
};

export const getLang = () => localStorage.getItem(KEY) || "en";
const markHtml = (l) => { document.documentElement.lang = l === "hi" ? "hi" : "en"; };
markHtml(getLang());

const fill = (s, v) => (v ? s.replace(/\{(\w+)\}/g, (_, k) => v[k] ?? "") : s);

export function useLang() {
  const [lang, setLangState] = useState(getLang);
  useEffect(() => {
    const sync = () => setLangState(getLang());
    window.addEventListener("nv:lang", sync);
    return () => window.removeEventListener("nv:lang", sync);
  }, []);
  const setLang = (l) => { localStorage.setItem(KEY, l); markHtml(l); window.dispatchEvent(new Event("nv:lang")); };
  const t = (s, v) => fill((lang === "hi" && HI[s]) || s, v);
  // "Venus / Saturn" style pairs and "Krishna Dashami" style phrases
  const tp = (s, sep = " / ") => s.split(sep).map((x) => t(x)).join(sep);
  return { lang, setLang, t, tp, locale: lang === "hi" ? "hi-IN" : "en-IN" };
}
