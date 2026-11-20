// 01-security.groovy
// Creates the admin account, enables matrix-free "logged in users can do
// anything" security, and sets the executor count on first boot.
import hudson.security.FullControlOnceLoggedInAuthorizationStrategy
import hudson.security.HudsonPrivateSecurityRealm
import jenkins.model.Jenkins

def instance = Jenkins.getInstanceOrNull()
if (instance == null) {
    return
}

def env = System.getenv()
def adminId = env.get('JENKINS_ADMIN_ID') ?: 'admin'
def adminPassword = env.get('JENKINS_ADMIN_PASSWORD')
def rootUrl = env.get('JENKINS_ROOT_URL') ?: 'http://localhost:8080/'

if (adminPassword == null || adminPassword.trim().isEmpty()) {
    println '[init] JENKINS_ADMIN_PASSWORD not set - skipping security setup'
    return
}

if (instance.getSecurityRealm() instanceof HudsonPrivateSecurityRealm) {
    println '[init] security realm already configured - skipping'
} else {
    def realm = new HudsonPrivateSecurityRealm(false, false, null)
    realm.createAccount(adminId, adminPassword)
    instance.setSecurityRealm(realm)

    def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
    strategy.setAllowAnonymousRead(false)
    instance.setAuthorizationStrategy(strategy)
    println "[init] created admin user '${adminId}'"
}

instance.setNumExecutors(2)
instance.setRootUrl(rootUrl.endsWith('/') ? rootUrl : rootUrl + '/')
instance.save()

println "[init] Jenkins URL = ${instance.getRootUrl()}, executors = ${instance.getNumExecutors()}"
