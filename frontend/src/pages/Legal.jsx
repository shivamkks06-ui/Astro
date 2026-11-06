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
  verification: ["Astrologer Verification Policy", [
    "Every astrologer applies through the in-app Studio with a government ID, qualification documents, experience, languages, expertise and per-minute prices.",
    "Identity and credentials are reviewed separately by our admin team. \"Identity checked\" means the government ID matched the applicant. \"Credentials reviewed\" means the qualification documents were reviewed. Neither badge appears until that specific review is approved.",
    "Only admin-approved astrologers with an active listing appear in Discover and can be booked. Applications can be approved, rejected with a reason, or sent back for resubmission.",
    "Identity documents are stored privately. They are never shown to customers or other astrologers.",
    "Ratings and reviews are shown only when they come from real completed consultations. We do not create or edit reviews.",
    "Verification confirms identity and documents only. It does not guarantee the accuracy of any reading.",
  ]],
  support: ["Contact & Support", [
    "For a problem with a consultation, open the booking from Account → Bookings and use Report or Dispute there, within the dispute window shown at booking. This links your request to the right session.",
    "For a safety concern, use Report or Block on the astrologer's profile or in the chat. Safety reports are reviewed by our team.",
    "To download or delete your data, go to Account → Privacy. Deletion requests are processed by our team, and the status is shown there.",
    "How your birth details are used: they are used only to calculate charts and reports. They are stored only if you save a chart or a birth profile, and only you can see them. Astrologers see birth details only when you share them in a booking.",
    "Payments: prices are shown per minute before you book, and refunds follow the Refund & Cancellation Policy.",
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
