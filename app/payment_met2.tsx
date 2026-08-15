import { FormEvent, useState } from "react";
import image from "./image.svg";
import maskGroup from "./mask-group.png";
import vector from "./vector.svg";
import vector2 from "./vector-2.svg";

const initialCard = {
  cardholderName: "Zinnatun",
  cardNumber: "456 667 689 777",
  expiryDate: "04/28",
  cvv: "677",
};

export const PaymentMethod = (): JSX.Element => {
  const [cardholderName, setCardholderName] = useState(
    initialCard.cardholderName,
  );
  const [cardNumber, setCardNumber] = useState(initialCard.cardNumber);
  const [expiryDate, setExpiryDate] = useState(initialCard.expiryDate);
  const [cvv, setCvv] = useState(initialCard.cvv);
  const [saveMessage, setSaveMessage] = useState("");

  const formatCardNumber = (value: string) => {
    const digits = value.replace(/\D/g, "").slice(0, 12);
    return digits.replace(/(\d{3})(?=\d)/g, "$1 ").trim();
  };

  const formatExpiryDate = (value: string) => {
    const digits = value.replace(/\D/g, "").slice(0, 4);

    if (digits.length <= 2) {
      return digits;
    }

    return `${digits.slice(0, 2)}/${digits.slice(2)}`;
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (
      !cardholderName.trim() ||
      !cardNumber.trim() ||
      !expiryDate.trim() ||
      !cvv.trim()
    ) {
      setSaveMessage("Please complete all card details.");
      return;
    }

    setSaveMessage("Card saved successfully.");
  };

  const handleBack = () => {
    if (window.history.length > 1) {
      window.history.back();
    }
  };

  return (
    <main className="bg-white w-full min-w-[360px] min-h-[800px] relative overflow-hidden">
      <div className="absolute top-0 left-0 w-[360px] h-7 bg-[#ecf1ff] rounded-tr-[36px]" />
      <header>
        <button
          type="button"
          onClick={handleBack}
          aria-label="Go back"
          className="absolute top-[62px] left-[29px] w-2.5 h-4 cursor-pointer"
        >
          <img className="w-2.5 h-4" alt="" src={vector} aria-hidden="true" />
        </button>
        <h1 className="absolute top-[60px] left-[calc(50.00%_-_113px)] w-[226px] [font-family:'League_Spartan-SemiBold',Helvetica] font-semibold text-[#225fff] text-2xl text-center tracking-[0] leading-[normal] whitespace-nowrap">
          Add Card
        </h1>
      </header>
      <section aria-label="Card preview">
        <div className="absolute top-[109px] left-[30px] w-[300px] h-[179px] bg-[#225fff] rounded-2xl" />
        <img
          className="absolute top-[109px] left-[30px] w-[300px] h-[179px] pointer-events-none"
          alt=""
          src={maskGroup}
          aria-hidden="true"
        />
        <img
          className="absolute top-[123px] left-[264px] w-[50px] h-[13px] pointer-events-none"
          alt=""
          src={vector2}
          aria-hidden="true"
        />
        <div className="absolute top-[209px] left-[57px] w-[190px] h-3.5 flex items-center [font-family:'League_Spartan-Bold',Helvetica] font-bold text-white text-xl tracking-[0] leading-[normal] whitespace-nowrap">
          {cardNumber || "456 667 689 777"}
        </div>
        <div className="absolute top-[238px] left-[57px] w-[103px] h-[15px] flex items-center [font-family:'League_Spartan-Regular',Helvetica] font-normal text-white text-xs tracking-[0] leading-[normal]">
          Card Holder Name
        </div>
        <div className="absolute top-[259px] left-[60px] w-[92px] h-4 flex items-center [font-family:'League_Spartan-Bold',Helvetica] font-bold text-white text-sm tracking-[0] leading-[normal] whitespace-nowrap">
          {cardholderName || "Zinnatun"}
        </div>
        <div className="absolute top-[253px] left-[180px] w-[52px] h-[15px] [font-family:'League_Spartan-Bold',Helvetica] font-bold text-white text-sm flex items-center tracking-[0] leading-[normal] whitespace-nowrap">
          {expiryDate || "04/28"}
        </div>
        <img
          className="absolute top-60 left-[284px] w-[29px] h-[25px] pointer-events-none"
          alt=""
          src={image}
          aria-hidden="true"
        />
      </section>
      <form onSubmit={handleSubmit} noValidate>
        <div className="absolute top-[315px] left-[31px] w-[180px] h-[22px] flex items-center [font-family:'League_Spartan-Regular',Helvetica] font-normal text-black text-lg tracking-[0] leading-[normal]">
          <label htmlFor="cardholder-name">Card Holder Name</label>
        </div>
        <input
          id="cardholder-name"
          name="cardholderName"
          type="text"
          value={cardholderName}
          onChange={(event) => setCardholderName(event.target.value)}
          autoComplete="cc-name"
          className="absolute top-[344px] left-[30px] w-[300px] h-11 bg-[#ecf1ff] rounded-[20px] px-[27px] [font-family:'League_Spartan-Regular',Helvetica] font-normal text-[#7f9bff] text-xl tracking-[0] leading-[normal]"
        />
        <div className="absolute top-[412px] left-[31px] w-[180px] h-[22px] flex items-center [font-family:'League_Spartan-Regular',Helvetica] font-normal text-black text-lg tracking-[0] leading-[normal]">
          <label htmlFor="card-number">Card Number</label>
        </div>
        <input
          id="card-number"
          name="cardNumber"
          type="text"
          inputMode="numeric"
          value={cardNumber}
          onChange={(event) =>
            setCardNumber(formatCardNumber(event.target.value))
          }
          autoComplete="cc-number"
          className="absolute top-[443px] left-[30px] w-[300px] h-11 bg-[#ecf1ff] rounded-[20px] px-[15px] [font-family:'League_Spartan-Regular',Helvetica] font-normal text-black text-xl tracking-[0] leading-[normal]"
        />
        <div className="absolute top-[512px] left-[31px] w-[180px] h-[22px] flex items-center [font-family:'League_Spartan-Regular',Helvetica] font-normal text-black text-lg tracking-[0] leading-[normal]">
          <label htmlFor="expiry-date">Expiry Date</label>
        </div>
        <input
          id="expiry-date"
          name="expiryDate"
          type="text"
          inputMode="numeric"
          value={expiryDate}
          onChange={(event) =>
            setExpiryDate(formatExpiryDate(event.target.value))
          }
          autoComplete="cc-exp"
          className="absolute top-[539px] left-[30px] w-[162px] h-11 bg-[#ecf1ff] rounded-[20px] px-[27px] [font-family:'League_Spartan-Regular',Helvetica] font-normal text-[#7f9bff] text-xl tracking-[0] leading-[normal]"
        />
        <div className="absolute top-[512px] left-[201px] w-[108px] h-[22px] flex items-center [font-family:'League_Spartan-Regular',Helvetica] font-normal text-black text-lg tracking-[0] leading-[normal]">
          <label htmlFor="cvv">Cvv</label>
        </div>
        <input
          id="cvv"
          name="cvv"
          type="password"
          inputMode="numeric"
          value={cvv}
          onChange={(event) =>
            setCvv(event.target.value.replace(/\D/g, "").slice(0, 4))
          }
          autoComplete="cc-csc"
          className="absolute top-[539px] left-[200px] w-[130px] h-11 bg-[#ecf1ff] rounded-[20px] px-[27px] [font-family:'League_Spartan-Regular',Helvetica] font-normal text-[#7f9bff] text-xl tracking-[0] leading-[normal]"
        />
        <button
          type="submit"
          className="absolute top-[688px] left-8 w-[297px] h-[45px] bg-[#225fff] rounded-[30px] cursor-pointer [font-family:'League_Spartan-Medium',Helvetica] font-medium text-white text-2xl text-center tracking-[0] leading-[normal]"
        >
          Save Card
        </button>
        <p className="sr-only" role="status" aria-live="polite">
          {saveMessage}
        </p>
      </form>
    </main>
  );
};
