from datetime import datetime, timedelta
from random import Random
from typing import List

from faker import Faker

from app.models import Email

SEED = 42
BASE_DATE = datetime(2024, 1, 15, 12, 0, 0)


def _seeded_tools() -> tuple[Faker, Random]:
    fake = Faker()
    fake.seed_instance(SEED)
    return fake, Random(SEED)


def _local_part(name: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "." for char in name)
    while ".." in cleaned:
        cleaned = cleaned.replace("..", ".")
    return cleaned.strip(".")


def _timestamp(rng: Random) -> datetime:
    days_ago = rng.randint(0, 6)
    hours_ago = rng.randint(0, 23)
    minutes_ago = rng.randint(0, 59)
    return BASE_DATE - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)


def _email(
    *,
    email_id: str,
    subject: str,
    sender: str,
    domain: str,
    body: str,
    rng: Random,
    thread_id: str | None = None,
    is_reply: bool = False,
) -> Email:
    return Email(
        id=email_id,
        subject=subject,
        sender=sender,
        sender_email=f"{_local_part(sender)}@{domain}",
        body=body,
        timestamp=_timestamp(rng),
        thread_id=thread_id,
        is_reply=is_reply,
    )


def get_task1_inbox() -> List[Email]:
    fake, rng = _seeded_tools()
    coworker = fake.name()
    project_manager = fake.name()
    friend = fake.first_name()
    utility_company = fake.company()

    emails = [
        _email(
            email_id="task1_email_01",
            subject="Final notice: claim your lottery payout today",
            sender=fake.name(),
            domain="winner-claims.net",
            body=(
                "We are pleased to inform you that your email was selected in our global lottery draw. "
                "To receive the funds, reply with your legal name, address, and a copy of your ID. "
                "The transfer window closes tonight, so immediate action is required. "
                "Our finance desk is waiting for your confirmation."
            ),
            rng=rng,
        ),
        _email(
            email_id="task1_email_02",
            subject="Discount medication shipped discreetly",
            sender=fake.company(),
            domain="medic-direct.shop",
            body=(
                "We now offer premium wellness pills without a prescription at a limited promotional rate. "
                "Most customers receive their package within three days and reorder right away. "
                "Click the secure payment link to unlock the wholesale discount. "
                "This campaign ends once inventory is cleared."
            ),
            rng=rng,
        ),
        _email(
            email_id="task1_email_03",
            subject="Confidential inheritance release file",
            sender=fake.name(),
            domain="estate-transfer.org",
            body=(
                "I am contacting you regarding an unclaimed inheritance connected to a deceased client with your surname. "
                "The funds can be released if you confirm a private banking contact today. "
                "This matter is sensitive, so please keep the conversation confidential. "
                "A quick reply will allow us to begin the transfer paperwork."
            ),
            rng=rng,
        ),
        _email(
            email_id="task1_email_04",
            subject="Remote job offer with immediate signing bonus",
            sender=fake.company(),
            domain="talent-fasttrack.co",
            body=(
                "Your profile was selected for a flexible remote role paying above market rates. "
                "No interview is required because the hiring manager has already approved your placement. "
                "Please send your home address and banking details so payroll can activate the signing bonus. "
                "Training starts as soon as we receive your information."
            ),
            rng=rng,
        ),
        _email(
            email_id="task1_email_05",
            subject="Urgent account verification required",
            sender="Security Desk",
            domain="mail-auth-support.net",
            body=(
                "We detected unusual sign-in activity on your mailbox earlier this morning. "
                "Your access will be suspended unless you confirm your password through the secure form below. "
                "The verification process takes less than one minute. "
                "Please act now to avoid permanent restrictions."
            ),
            rng=rng,
        ),
        _email(
            email_id="task1_email_06",
            subject="Double your crypto balance before midnight",
            sender=fake.company(),
            domain="coin-upgrade.io",
            body=(
                "A private investor group is matching all deposits for the next few hours. "
                "Participants who joined yesterday reported instant gains after the first transfer. "
                "Send any amount to the wallet listed below to activate your bonus. "
                "This invitation is not being shared publicly."
            ),
            rng=rng,
        ),
        _email(
            email_id="task1_email_07",
            subject="Can we move tomorrow's planning meeting to 11 AM?",
            sender=coworker,
            domain="northstar-analytics.com",
            body=(
                "I need to shift our planning meeting by thirty minutes because another call ran over. "
                "If 11 AM still works for you, I will update the calendar invite right away. "
                "I also attached the agenda so you can skim it beforehand. "
                "Let me know if a later slot would be easier."
            ),
            rng=rng,
        ),
        _email(
            email_id="task1_email_08",
            subject="Project update: client approved the revised timeline",
            sender=project_manager,
            domain="northstar-analytics.com",
            body=(
                "The client signed off on the revised rollout plan this afternoon. "
                "We can keep the current milestone dates as long as the design review happens by Thursday. "
                "I summarized the open risks in the shared document. "
                "Please glance at the notes before tomorrow's standup."
            ),
            rng=rng,
        ),
        _email(
            email_id="task1_email_09",
            subject=f"Reminder: your {utility_company} bill is due on Friday",
            sender=utility_company,
            domain="billing-notices.com",
            body=(
                "This is a reminder that your latest balance is scheduled for payment on Friday. "
                "You can pay online, by phone, or through automatic withdrawal if that is already enabled. "
                "If payment has already been submitted, no further action is needed. "
                "Thank you for staying on top of your account."
            ),
            rng=rng,
        ),
        _email(
            email_id="task1_email_10",
            subject="Dinner this weekend?",
            sender=f"{friend} Patel",
            domain="gmail.com",
            body=(
                "Hey, I was thinking it would be nice to catch up over dinner this weekend. "
                "I found a new place near the station that looks pretty good. "
                "Saturday evening is best for me, but I can make Sunday work too. "
                "Tell me what your schedule looks like."
            ),
            rng=rng,
        ),
    ]
    return emails


def get_task2_inbox() -> tuple[List[Email], dict]:
    fake, rng = _seeded_tools()
    emails = [
        _email(
            email_id="task2_email_01",
            subject="Urgent: production access request needs approval",
            sender=fake.name(),
            domain="acme-ops.com",
            body=(
                "The deployment team is blocked waiting for approval on the production access request. "
                "We need a response before the maintenance window starts this afternoon. "
                "I included the change summary and rollback plan below. "
                "Please confirm whether we can proceed."
            ),
            rng=rng,
        ),
        _email(
            email_id="task2_email_02",
            subject="Please review the exec brief before 4 PM",
            sender=fake.name(),
            domain="acme-ops.com",
            body=(
                "Leadership asked for a final pass on the executive brief before it goes out today. "
                "Most of the numbers are already locked, but the customer risk section still needs attention. "
                "If you can send comments by 4 PM, I can fold them in before distribution. "
                "Thanks for turning this around quickly."
            ),
            rng=rng,
        ),
        _email(
            email_id="task2_email_03",
            subject="Need sign-off on contract changes today",
            sender=fake.name(),
            domain="legal-partners.com",
            body=(
                "The vendor accepted most of our redlines, but two terms still need internal approval. "
                "Procurement wants a final answer today so the purchase order can be released. "
                "I highlighted the disputed language in the attached markup. "
                "Please let me know how you want to handle it."
            ),
            rng=rng,
        ),
        _email(
            email_id="task2_email_04",
            subject="Roadmap sync next Tuesday",
            sender=fake.name(),
            domain="northstar-analytics.com",
            body=(
                "I would like to schedule a roadmap sync for next Tuesday afternoon. "
                "The goal is to confirm dependencies before we lock the Q2 delivery plan. "
                "A forty-five minute slot should be enough if the core team can attend. "
                "Send over your availability and I will put something on the calendar."
            ),
            rng=rng,
        ),
        _email(
            email_id="task2_email_05",
            subject="Can we book time for the vendor demo?",
            sender=fake.name(),
            domain="vendor-success.io",
            body=(
                "Our solutions engineer is available on Wednesday and Thursday for the demo. "
                "We can tailor the walkthrough to your reporting workflow if we know who will attend. "
                "Please share a preferred time and any topics you want covered. "
                "I will send a calendar invite once I hear back."
            ),
            rng=rng,
        ),
        _email(
            email_id="task2_email_06",
            subject="Invoice INV-2048 for monthly hosting",
            sender=fake.company(),
            domain="cloudledger.com",
            body=(
                "Attached is invoice INV-2048 covering this month's managed hosting charges. "
                "Payment is due within fourteen days according to the service agreement. "
                "If you need a purchase order reference added, reply and I will update the record. "
                "Thank you for your continued business."
            ),
            rng=rng,
        ),
        _email(
            email_id="task2_email_07",
            subject="Consulting invoice for March design support",
            sender=fake.company(),
            domain="studio-finance.co",
            body=(
                "Please find the March consulting invoice attached for the completed design support work. "
                "The total reflects the approved change request from last week. "
                "Payment terms remain net fifteen. "
                "Let me know if your accounting team needs anything else."
            ),
            rng=rng,
        ),
        _email(
            email_id="task2_email_08",
            subject="Product Ops Weekly: top stories and templates",
            sender=fake.company(),
            domain="newsletter.productopsweekly.com",
            body=(
                "This week's edition covers launch checklists, stakeholder templates, and a new case study on onboarding. "
                "We also linked a short interview with an operations lead from a fast-growing startup. "
                "If you missed last week's issue, the archive is available from the footer link. "
                "See you again next Monday."
            ),
            rng=rng,
        ),
        _email(
            email_id="task2_email_09",
            subject="SaaS Benchmarks Digest for April",
            sender=fake.company(),
            domain="digest.saasbenchmarks.org",
            body=(
                "The April benchmark report compares retention, payback periods, and expansion revenue across mid-market teams. "
                "We included a short analysis of the trends that changed most over the last quarter. "
                "Subscribers can download the spreadsheet and presentation deck from the member portal. "
                "Feedback is always welcome."
            ),
            rng=rng,
        ),
        _email(
            email_id="task2_email_10",
            subject="Community Roundup: events, jobs, and resources",
            sender=fake.company(),
            domain="updates.communityroundup.net",
            body=(
                "Here is your weekly roundup of community events, open roles, and new learning resources. "
                "This issue includes a practical guide to writing stronger status updates. "
                "You can update your subscription settings at any time from the preferences page. "
                "Thanks for reading."
            ),
            rng=rng,
        ),
        _email(
            email_id="task2_email_11",
            subject="Are you free for dinner on Friday?",
            sender=fake.name(),
            domain="gmail.com",
            body=(
                "I will be in your part of town on Friday and thought it would be fun to grab dinner. "
                "There is a new cafe near your office that people keep recommending. "
                "If Friday is tough, I can also do Saturday afternoon. "
                "Let me know what works."
            ),
            rng=rng,
        ),
        _email(
            email_id="task2_email_12",
            subject="Photos from the weekend trip",
            sender=fake.name(),
            domain="icloud.com",
            body=(
                "I finally sorted through the photos from the weekend trip and uploaded the best ones. "
                "There are a few great candid shots that I think you will like. "
                "I can send the full album if you want the originals. "
                "Hope your week is going well."
            ),
            rng=rng,
        ),
        _email(
            email_id="task2_email_13",
            subject="Claim your tax refund in minutes",
            sender=fake.company(),
            domain="refund-now-central.net",
            body=(
                "Our records show you are eligible for an immediate tax refund through our direct release process. "
                "Complete the short form and provide your bank information to receive the payment today. "
                "This opportunity expires within the next few hours. "
                "Do not miss your chance to collect what is owed to you."
            ),
            rng=rng,
        ),
        _email(
            email_id="task2_email_14",
            subject="Gift card verification needed",
            sender="Office Desk",
            domain="it-helpfast.org",
            body=(
                "A manager asked us to help process gift cards for an urgent client gesture. "
                "Purchase the cards right away and send the codes back by reply so finance can reimburse you. "
                "Time is critical because the client is waiting. "
                "Please confirm once this is done."
            ),
            rng=rng,
        ),
        _email(
            email_id="task2_email_15",
            subject="Private trading method that beats the market",
            sender=fake.company(),
            domain="wealth-signal.pro",
            body=(
                "A small group of early members is using our private trading method to generate daily returns. "
                "The starter course is free if you register before midnight and confirm your contact details. "
                "Many students double their account size within the first week. "
                "Reserve your place before enrollment closes."
            ),
            rng=rng,
        ),
    ]
    labels = {
        "task2_email_01": {"label": "urgent_work"},
        "task2_email_02": {"label": "urgent_work"},
        "task2_email_03": {"label": "urgent_work"},
        "task2_email_04": {"label": "meeting_request"},
        "task2_email_05": {"label": "meeting_request"},
        "task2_email_06": {"label": "invoice"},
        "task2_email_07": {"label": "invoice"},
        "task2_email_08": {"label": "newsletter"},
        "task2_email_09": {"label": "newsletter"},
        "task2_email_10": {"label": "newsletter"},
        "task2_email_11": {"label": "personal"},
        "task2_email_12": {"label": "personal"},
        "task2_email_13": {"label": "spam"},
        "task2_email_14": {"label": "spam"},
        "task2_email_15": {"label": "spam"},
    }
    return emails, labels


def get_task3_inbox() -> List[Email]:
    fake, rng = _seeded_tools()
    shipping_thread = "task3_thread_shipping_01"
    support_thread = "task3_thread_support_01"
    shipping_customer = fake.name()
    login_customer = fake.name()

    emails = [
        _email(
            email_id="task3_email_01",
            subject="My blender stopped working after two uses",
            sender=fake.name(),
            domain="gmail.com",
            body=(
                "I bought your blender last month and it already stopped turning on after only two uses. "
                "I followed the setup instructions carefully and the outlet is working for other appliances. "
                "This has been really frustrating because I needed it for daily meal prep. "
                "Please let me know what my options are for a replacement or repair."
            ),
            rng=rng,
        ),
        _email(
            email_id="task3_email_02",
            subject="Requesting a refund for order 18473",
            sender=fake.name(),
            domain="outlook.com",
            body=(
                "I returned order 18473 last week and I have not seen the refund hit my card yet. "
                "The tracking page shows the package was delivered back to your warehouse on Monday. "
                "Could you confirm the refund status and expected timeline? "
                "I would appreciate an update as soon as possible."
            ),
            rng=rng,
        ),
        _email(
            email_id="task3_email_03",
            subject="Where is my shipment for order 20911?",
            sender=shipping_customer,
            domain="yahoo.com",
            body=(
                "The estimated delivery date for order 20911 was yesterday, but the tracking link has not updated. "
                "I need the package before the weekend because it is a birthday gift. "
                "Can you check whether the shipment is delayed or lost in transit? "
                "Thanks for any help you can provide."
            ),
            rng=rng,
            thread_id=shipping_thread,
        ),
        _email(
            email_id="task3_email_04",
            subject="Login code never arrives",
            sender=login_customer,
            domain="hotmail.com",
            body=(
                "I am trying to sign in to my account, but the one-time login code never reaches my inbox. "
                "I checked spam and tried again from two different browsers with the same result. "
                "Because of this, I cannot access the subscription features I paid for. "
                "Please advise on how to get back in."
            ),
            rng=rng,
            thread_id=support_thread,
        ),
        _email(
            email_id="task3_email_05",
            subject="Incorrect charge on my latest statement",
            sender=fake.name(),
            domain="protonmail.com",
            body=(
                "I noticed a billing charge on my latest statement that does not match the plan shown in my account. "
                "The invoice lists an add-on that I never selected during checkout. "
                "I need someone to review the charge and explain how it was applied. "
                "Please investigate this billing dispute promptly."
            ),
            rng=rng,
        ),
        _email(
            email_id="task3_email_06",
            subject="Do you offer gift receipts?",
            sender=fake.name(),
            domain="gmail.com",
            body=(
                "I am planning to place an order for a family member and wanted to ask if you offer gift receipts. "
                "It would also help to know whether prices are hidden on the packing slip. "
                "I could not find this information on the checkout page. "
                "Thanks in advance for clarifying."
            ),
            rng=rng,
        ),
        _email(
            email_id="task3_email_07",
            subject="Following up on the missing login code",
            sender=login_customer,
            domain="hotmail.com",
            body=(
                "I am following up because I still have not received any login code after trying again this morning. "
                "The issue is affecting my work because I cannot download the files stored in my account. "
                "If there is an alternate verification method, I am happy to use it right away. "
                "Please help me resolve this today."
            ),
            rng=rng,
            thread_id=support_thread,
            is_reply=True,
        ),
        _email(
            email_id="task3_email_08",
            subject="Follow-up: shipping update still unavailable",
            sender=shipping_customer,
            domain="yahoo.com",
            body=(
                "I wanted to follow up on order 20911 because the tracking page is still frozen with no movement. "
                "The original delivery date has now passed and I have not received any carrier notice. "
                "Please check whether a replacement shipment should be sent. "
                "I would really appreciate a concrete update."
            ),
            rng=rng,
            thread_id=shipping_thread,
            is_reply=True,
        ),
    ]
    return emails
