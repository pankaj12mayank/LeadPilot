export interface PaymentFailedData {
  userName: string;
  planName: string;
  amount: string;
  currency: string;
  failureReason: string;
  retryUrl: string;
}

export function getPaymentFailedEmail(data: PaymentFailedData): string {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Payment Failed - LeadPilot</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f9fafb; color: #1f2937;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f9fafb;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); overflow: hidden;">
          <tr>
            <td style="background: linear-gradient(135deg, #d97706 0%, #f59e0b 100%); padding: 32px 40px; text-align: center;">
              <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #ffffff;">LeadPilot</h1>
            </td>
          </tr>
          <tr>
            <td style="padding: 40px;">
              <h2 style="margin: 0 0 24px 0; font-size: 24px; font-weight: 600; color: #dc2626;">Payment Failed</h2>
              <p style="margin: 0 0 16px 0; font-size: 16px; line-height: 1.6; color: #4b5563;">Hi {{userName}},</p>
              <p style="margin: 0 0 24px 0; font-size: 16px; line-height: 1.6; color: #4b5563;">We were unable to process your payment for the <strong>{{planName}}</strong> plan. Your subscription has not been charged.</p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; margin-bottom: 24px;">
                <tr>
                  <td style="padding: 20px;">
                    <p style="margin: 0 0 12px 0; font-size: 14px; font-weight: 600; color: #dc2626;">Reason:</p>
                    <p style="margin: 0; font-size: 16px; color: #991b1b;">{{failureReason}}</p>
                    <hr style="margin: 16px 0; border: none; border-top: 1px solid #fecaca;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                      <tr>
                        <td style="padding: 4px 0; font-size: 14px; color: #991b1b;">Plan</td>
                        <td style="padding: 4px 0; font-size: 14px; font-weight: 600; color: #991b1b; text-align: right;">{{planName}}</td>
                      </tr>
                      <tr>
                        <td style="padding: 4px 0; font-size: 14px; color: #991b1b;">Amount</td>
                        <td style="padding: 4px 0; font-size: 14px; font-weight: 600; color: #991b1b; text-align: right;">{{currency}}{{amount}}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
              <p style="margin: 0 0 24px 0; font-size: 16px; line-height: 1.6; color: #4b5563;">Please review your payment details and try again. If you need assistance, our support team is here to help.</p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td align="center">
                    <a href="{{retryUrl}}" style="display: inline-block; background-color: #d97706; color: #ffffff; text-decoration: none; font-size: 16px; font-weight: 600; padding: 14px 32px; border-radius: 8px;">Try Again</a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="background-color: #f9fafb; padding: 24px 40px; text-align: center; border-top: 1px solid #e5e7eb;">
              <p style="margin: 0 0 8px 0; font-size: 14px; color: #6b7280;">© 2026 LeadPilot. All rights reserved.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;

  return html
    .replace(/\{\{userName\}\}/g, data.userName)
    .replace(/\{\{planName\}\}/g, data.planName)
    .replace(/\{\{amount\}\}/g, data.amount)
    .replace(/\{\{currency\}\}/g, data.currency)
    .replace(/\{\{failureReason\}\}/g, data.failureReason)
    .replace(/\{\{retryUrl\}\}/g, data.retryUrl);
}