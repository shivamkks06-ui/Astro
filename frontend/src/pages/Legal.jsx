import { useParams, Link } from "react-router-dom";

const DOCS = {
  terms: ["Terms of Service", [
    "NakshatraVeda is a marketplace that connects customers with independent astrologers. Astrologers are not our employees.",
    "Astrology consultations are interpretive and spiritual guidance only. They are not medical, legal, financial or psychological advice, and nothing said in a consultation is a guaranteed outcome.",
    "Prices are shown before booking and fixed once you send a request. Payment is collected through our payment partner. We never store card numbers, UPI PINs or payment credentials.",
    "We may suspend accounts that break these terms or our Community Guidelines.",
    "[Placeholder: registered business name, address, governing law and grievance officer details to be added by the platform owner.]",
  ]],
  privacy: ["Privacy Policy", [
    "We collect your account details, any birth details you choose to save, booking records, chat messages and payment references.",
    "Birth details are shared with an astrologer only for a confirmed booking, and only if you allow it in Privacy settings.",
    "Astrologer identity and qualification documents are kept in private storage. Only authorised reviewers can open them, through short-lived links, and every access is logged.",
    "Audio and video calls are not recorded by default.",
    "You can download a copy of your data and request account deletion from your account's Privacy tab. Financial records are kept as long as the law requires.",
    "[Placeholder: data controller contact and retention periods to be added by the platform owner.]",
  ]],
  guidelines: ["Community Guidelines & Acceptable Use", [
    "Astrologers must never make guaranteed claims about marriage, health, money, legal results or other life outcomes.",
    "No fear-based, coercive or manipulative language. No pressuring customers into more sessions, remedies or purchases.",
    "Never advise anyone to stop medical treatment, or to make legal or financial decisions on astrological grounds alone.",
    "Be respectful. Harassment, hate, sexual content and asking for contact or payment outside the platform are not allowed.",
    "If something feels wrong, use Report on the astrologer's profile or the booking page, or block the person. Our team reviews every report. If you are in crisis or danger, contact local emergency services.",
  ]],
  refunds: ["Refund & Cancellation Policy", [
    "Cancellations made before the cancellation window (shown at booking, 2 hours by default) get a full refund. Later cancellations get a partial refund at the percentage shown at booking.",
    "If an astrologer cancels, declines or doesn't start the session: full refund.",
    "If the astrologer ends a session early: pro-rata refund for unused minutes. If you leave early, there's no refund.",
    "Audio/video sessions that never connect are not charged.",
    "You can raise a dispute within the dispute window shown at booking. Our team reviews it and may issue a full or partial refund.",
  ]],
};

export default function Legal() {
  const { slug } = useParams();
  const doc = DOCS[slug] || DOCS.terms;
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-8 py-16">
      <p className="overline mb-2">Policies</p>
      <h1 data-testid="legal-title" className="text-3xl sm:text-4xl mb-8">{doc[0]}</h1>
      <div className="space-y-4">{doc[1].map((p, i) => <p key={i} className="text-slate-300 leading-relaxed">{p}</p>)}</div>
      <div className="flex flex-wrap gap-4 mt-12 text-sm">{Object.entries(DOCS).map(([k, v]) => <Link key={k} to={`/legal/${k}`} className="inline-flex items-center min-h-11 text-amber-300 hover:underline">{v[0]}</Link>)}</div>
    </div>
  );
}
