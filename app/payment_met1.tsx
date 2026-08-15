import { useState } from "react";
import ellipse35 from "./ellipse-35.svg";
import image from "./image.svg";
import vector from "./vector.svg";
import vector2 from "./vector-2.svg";
import vector3 from "./vector-3.svg";

type PaymentOption = "card" | "apple" | "paypal" | "google";

const paymentOptions: Array<{
  id: PaymentOption;
  label: string;
  icon: string;
  iconClassName: string;
  topClassName: string;
  textTopClassName: string;
}> = [
  {
    id: "card",
    label: "Add New Card",
    icon: image,
    iconClassName: "absolute top-3 left-[15px] w-[26px] h-5",
    topClassName: "top-[161px]",
    textTopClassName: "top-[13px]",
  },
  {
    id: "apple",
    label: "Apple Play",
    icon: vector2,
    iconClassName: "absolute top-2 left-[17px] w-[22px] h-[26px]",
    topClassName: "top-[284px]",
    textTopClassName: "top-[15px]",
  },
  {
    id: "paypal",
    label: "Paypal",
    icon: vector3,
    iconClassName: "absolute top-2 left-[19px] w-[17px] h-6",
    topClassName: "top-[336px]",
    textTopClassName: "top-[14px]",
  },
  {
    id: "google",
    label: "Google Play",
    icon: ellipse35,
    iconClassName: "absolute top-3 left-[18px] w-5 h-5",
    topClassName: "top-[388px]",
    textTopClassName: "top-[14px]",
  },
];

export const PaymentMethod = (): JSX.Element => {
  const [selectedPayment, setSelectedPayment] = useState<PaymentOption>("card");

  const handleBack = () => {
    if (typeof window !== "undefined" && window.history.length > 1) {
      window.history.back();
    }
  };

  return (
    <main className="relative min-h-[800px] min-w-[360px] w-full overflow-hidden bg-white">
      <div
        className="absolute top-0 left-0 h-7 w-[360px] bg-[#ecf1ff]"
        aria-hidden="true"
      />
      <header>
        <button
          type="button"
          onClick={handleBack}
          className="absolute top-[60px] left-[29px] flex h-5 w-5 items-center justify-center"
          aria-label="Go back"
        >
          <img className="h-4 w-2.5" alt="" src={vector} />
        </button>
        <h1 className="absolute top-[60px] left-[calc(50.00%_-_113px)] w-[226px] whitespace-nowrap text-center [font-family:'League_Spartan-SemiBold',Helvetica] text-2xl font-semibold leading-[normal] tracking-[0] text-[#225fff]">
          Payment Method
        </h1>
      </header>
      <section aria-labelledby="card-payment-heading">
        <h2
          id="card-payment-heading"
          className="absolute top-[126px] left-[31px] flex h-[22px] w-[180px] items-center whitespace-nowrap [font-family:'League_Spartan-Regular',Helvetica] text-xl font-normal leading-[normal] tracking-[0] text-black"
        >
          Credit &amp; Debit Card
        </h2>
      </section>
      <section aria-labelledby="more-payment-heading">
        <h2
          id="more-payment-heading"
          className="absolute top-[249px] left-[31px] flex h-[22px] w-[180px] items-center whitespace-nowrap [font-family:'League_Spartan-Regular',Helvetica] text-xl font-normal leading-[normal] tracking-[0] text-black"
        >
          More Payment Option
        </h2>
      </section>
      <fieldset className="m-0 border-0 p-0" aria-label="Select payment method">
        <legend className="sr-only">Payment method</legend>
        {paymentOptions.map((option) => {
          const isSelected = selectedPayment === option.id;

          return (
            <label
              key={option.id}
              className={`absolute left-[30px] ${option.topClassName} h-11 w-[300px] cursor-pointer rounded-[20px] bg-[#ecf1ff]`}
            >
              <input
                type="radio"
                name="payment-method"
                value={option.id}
                checked={isSelected}
                onChange={() => setSelectedPayment(option.id)}
                className="peer sr-only"
              />
              <img
                className={option.iconClassName}
                alt=""
                src={option.icon}
                aria-hidden="true"
              />
              <span
                className={`absolute left-[52px] ${option.textTopClassName} flex h-3.5 items-center whitespace-nowrap [font-family:'League_Spartan-Regular',Helvetica] text-xl font-normal leading-[normal] tracking-[0] text-[#7f9bff]`}
              >
                {option.label}
              </span>
              <span
                className="absolute top-[11px] left-[266px] h-5 w-5 rounded-[10px] border border-solid border-[#225fff]"
                aria-hidden="true"
              >
                {isSelected && (
                  <span className="absolute top-[3px] left-[3px] h-3 w-3 rounded-md bg-[#225fff]" />
                )}
              </span>
            </label>
          );
        })}
      </fieldset>
    </main>
  );
};
