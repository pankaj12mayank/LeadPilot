export interface SubscriptionExpiringData {
  userName: string;
  planName: string;
  expiryDate: string;
  renewUrl: string;
}

export function getSubscriptionExpiringEmail(data: SubscriptionExpiringData): string {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Subscription Expiring Soon - LeadPilot</title>
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
              <h2 style="margin: 0 0 24px 0; font-size: 24px; font-weight: 600; color: #111827;">Subscription Expiring Soon</h2>
              <p style="margin: 0 0 16px 0; font-size: 16px; line-height: 1.6; color: #4b5563;">Hi {{userName}},</p>
              <p style="margin: 0 0 24px 0; font-size: 16px; line-height: 1.6; color: #4b5563;">Your <strong>{{planName}}</strong> subscription will expire on <strong>{{expiryDate}}</strong>. Don't lose access to your leads and advanced features.</p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #fffbeb; border: 1px solid #fcd34d; border-radius: 8px; margin-bottom: 24px;">
                <tr>
                  <td style="padding: 20px;">
                    <p style="margin: 0 0 8px 0; font-size: 14px; font-weight: 600; color: #92400e;">What happens if you don't renew:</p>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px; line-height: 1.8; color: #92400e;">
                      <li>Access to exported leads will be limited</li>
                      <li>Advanced filtering features will be disabled</li>
                      <li>API access may be restricted</li>
                    </ul>
                  </td>
                </tr>
              </table>
              <p style="margin: 0 0 24px 0; font-size: 16px; line-height: 1.6; color: #4b5563;">Renew now to continue finding high-quality leads without interruption.</p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td align="center">
                    <a href="{{renewUrl}}" style="display: inline-block; background-color: #d97706; color: #ffffff; text-decoration: none; font-size: 16px; font-weight: 600; padding: 14px 32px; border-radius: 8px;">Renew Now</a>
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
    .replace(/\{\{expiryDate\}\}/g, data.expiryDate)
    .replace(/\{\{renewUrl\}\}/g, data.renewUrl);
}