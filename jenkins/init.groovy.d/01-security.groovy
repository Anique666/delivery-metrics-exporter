// 01-security.groovy
// Creates the admin account, enables "logged-in users can do anything"
// security, sets the root URL and the executor count on first boot.
//
// A fresh Jenkins can already contain an incomplete "admin" user record with
// no password (created during installation). Such a record cannot log in, so
// the script replaces it with a real account whose password comes from the
// JENKINS_ADMIN_PASSWORD environment variable.
import hudson.model.User
import hudson.security.FullControlOnceLoggedInAuthorizationStrategy
import hudson.security.HudsonPrivateSecurityRealm
import jenkins.model.Jenkins
import jenkins.model.JenkinsLocationConfiguration

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

try {
    def realm = instance.getSecurityRealm()
    if (!(realm instanceof HudsonPrivateSecurityRealm)) {
        realm = new HudsonPrivateSecurityRealm(false, false, null)
        instance.setSecurityRealm(realm)
        println '[init] installed HudsonPrivateSecurityRealm'
    }

    def created = false
    try {
        realm.createAccount(adminId, adminPassword)
        created = true
        println "[init] created admin user '${adminId}'"
    } catch (Throwable firstAttempt) {
        println "[init] account '${adminId}' could not be created (${firstAttempt.message}) - recreating"
        def incomplete = User.getById(adminId, false)
        if (incomplete != null) {
            incomplete.delete()
        }
        realm.createAccount(adminId, adminPassword)
        created = true
        println "[init] recreated admin user '${adminId}'"
    }

    if (!(instance.getAuthorizationStrategy() instanceof FullControlOnceLoggedInAuthorizationStrategy)) {
        def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
        strategy.setAllowAnonymousRead(false)
        instance.setAuthorizationStrategy(strategy)
        println '[init] enabled FullControlOnceLoggedInAuthorizationStrategy'
    }

    instance.setNumExecutors(2)

    def location = JenkinsLocationConfiguration.get()
    location.setUrl(rootUrl.endsWith('/') ? rootUrl : rootUrl + '/')
    location.save()

    instance.save()
    println "[init] Jenkins URL = ${location.getUrl()}, executors = ${instance.getNumExecutors()}, admin ready = ${created}"
} catch (Throwable failure) {
    println "[init] SECURITY SETUP FAILED: ${failure}"
    failure.printStackTrace()
}
