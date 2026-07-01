export interface WelcomeEmailData {
  userName: string;
  planName: string;
  leadLimit: string;
  loginUrl: string;
}

export function getWelcomeEmail(data: WelcomeEmailData): string {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Welcome to LeadPilot</title>
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
              <h2 style="margin: 0 0 24px 0; font-size: 24px; font-weight: 600; color: #111827;">Welcome to LeadPilot, {{userName}}!</h2>
              <p style="margin: 0 0 16px 0; font-size: 16px; line-height: 1.6; color: #4b5563;">Thank you for joining! We're excited to help you find your next batch of high-quality leads. You've made a great choice with the <strong>{{planName}}</strong> plan.</p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f3f4f6; border-radius: 8px; margin-bottom: 24px;">
                <tr>
                  <td style="padding: 20px;">
                    <p style="margin: 0 0 12px 0; font-size: 14px; font-weight: 600; color: #d97706; text-transform: uppercase; letter-spacing: 0.5px;">Your Plan</p>
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                      <tr>
                        <td style="padding: 6px 0; font-size: 14px; color: #6b7280;">Plan Name</td>
                        <td style="padding: 6px 0; font-size: 14px; font-weight: 600; color: #111827; text-align: right;">{{planName}}</td>
                      </tr>
                      <tr>
                        <td style="padding: 6px 0; font-size: 14px; color: #6b7280;">Monthly Leads</td>
                        <td style="padding: 6px 0; font-size: 14px; font-weight: 600; color: #059669; text-align: right;">{{leadLimit}} leads</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
              <p style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: #111827;">Getting Started:</p>
              <ol style="margin: 0 0 24px 0; padding-left: 20px; font-size: 15px; line-height: 1.8; color: #4b5563;">
                <li>Set up your target audience and industry preferences</li>
                <li>Use the lead search to find prospects matching your criteria</li>
                <li>Export and connect leads to your favorite CRM tools</li>
              </ol>
              <p style="margin: 0 0 24px 0; font-size: 16px; line-height: 1.6; color: #4b5563;">Need help getting started? Check out our documentation or reach out to our support team anytime.</p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td align="center">
                    <a href="{{loginUrl}}" style="display: inline-block; background-color: #d97706; color: #ffffff; text-decoration: none; font-size: 16px; font-weight: 600; padding: 14px 32px; border-radius: 8px;">Get Started</a>
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
    .replace(/\{\{leadLimit\}\}/g, data.leadLimit)
    .replace(/\{\{loginUrl\}\}/g, data.loginUrl);
}